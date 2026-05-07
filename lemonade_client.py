from openai import OpenAI
from pydantic import BaseModel, Field
from typing import Literal
import json
import requests
import time
from config import settings


class EmailCategory(BaseModel):
    name: Literal["work", "personal", "newsletters", "promotions", "notifications", "other"]
    count: int
    subjects: list[str] = Field(default_factory=list, max_length=5)  # Top 5


class EmailAnalysis(BaseModel):
    summary: str = Field(..., description="2-3 sentence summary of main topics")
    categories: list[EmailCategory]
    needs_response_ids: list[str] = Field(default_factory=list)
    urgent_count: int = 0


class LemonadeClient:
    def __init__(self):
        self.client = OpenAI(
            api_key=settings.lemonade_api_key,
            base_url=settings.lemonade_server_url,
            timeout=None
        )
        self.model = settings.lemonade_model
        self.base_url = settings.lemonade_server_url.replace("/v1", "")

    def _reload_model(self):
        try:
            unload_url = f"{self.base_url}/api/v1/unload"
            response = requests.post(
                unload_url,
                json={"model": self.model},
                headers={"Authorization": f"Bearer {settings.lemonade_api_key}"},
                timeout=10
            )
            if response.status_code == 200:
                print(f" Model '{self.model}' unloaded, KV cache cleared")
                time.sleep(1)
            else:
                print(f" Model unload returned {response.status_code}: {response.text}")
        except Exception as e:
            print(f" Could not unload model (continuing anyway): {e}")

    def analyze_emails(self, emails: list) -> EmailAnalysis:
        if not emails:
            return EmailAnalysis(
                summary="No emails received in the last 24 hours.",
                categories=[],
                needs_response_ids=[],
                urgent_count=0
            )

        chunk_size = 10
        chunks = [emails[i:i + chunk_size] for i in range(0, len(emails), chunk_size)]

        print(f"Analyzing {len(emails)} emails in {len(chunks)} chunks...")

        all_categories = {}
        all_needs_response = []
        all_urgent_count = 0
        chunk_summaries = []

        for i, chunk in enumerate(chunks):
            print(f"Processing chunk {i+1}/{len(chunks)} ({len(chunk)} emails)...")

            if i > 0:
                self._reload_model()

            try:
                chunk_result = self._analyze_chunk(chunk, i)

                print(f"\nChunk {i+1} completed:")
                print(f"  Summary: {chunk_result.summary}")
                print(f"  Categories found: {', '.join([f'{c.name}({c.count})' for c in chunk_result.categories])}")
                if chunk_result.needs_response_ids:
                    print(f"  Needs response: {len(chunk_result.needs_response_ids)} emails")
                if chunk_result.urgent_count > 0:
                    print(f"  Urgent: {chunk_result.urgent_count} emails")
                print()

                chunk_summaries.append(chunk_result.summary)

                for category in chunk_result.categories:
                    if category.name not in all_categories:
                        all_categories[category.name] = {
                            "count": 0,
                            "subjects": []
                        }
                    all_categories[category.name]["count"] += category.count
                    all_categories[category.name]["subjects"].extend(category.subjects)

                all_needs_response.extend(chunk_result.needs_response_ids)
                all_urgent_count += chunk_result.urgent_count

            except Exception as e:
                print(f"Error analyzing chunk {i+1}: {e}\n")
                continue

        # Build final result
        final_categories = [
            EmailCategory(
                name=name,
                count=data["count"],
                subjects=data["subjects"][:5]  # Top 5 overall
            )
            for name, data in all_categories.items()
        ]

        if chunk_summaries:
            if len(chunks) == 1:
                overall_summary = chunk_summaries[0]
            else:
                # Multiple chunks - combine with clear separation
                combined_parts = []
                for i, summary in enumerate(chunk_summaries):
                    combined_parts.append(f"Chunk {i+1}: {summary}")
                overall_summary = "\n\n".join(combined_parts)
        else:
            overall_summary = f"Received {len(emails)} emails. Analysis temporarily unavailable."

        return EmailAnalysis(
            summary=overall_summary,
            categories=final_categories,
            needs_response_ids=all_needs_response,
            urgent_count=all_urgent_count
        )

    def _analyze_chunk(self, emails: list, chunk_index: int) -> EmailAnalysis:
        email_data = []
        for i, email in enumerate(emails):
            email_data.append({
                "index": i,
                "id": email.message_id,
                "from": email.sender,
                "subject": email.subject,
                "snippet": email.snippet,
                "is_unread": email.is_unread
            })

        prompt = self._build_analysis_prompt(email_data)

        try:
            response = self.client.chat.completions.create(
                model=self.model,
                messages=[
                    {"role": "system", "content": "You are an email triage assistant. Output ONLY the JSON object. Start with { and end with }."},
                    {"role": "user", "content": prompt}
                ],
                temperature=0.3,
                extra_body={"chat_template_kwargs": {"enable_thinking": False}}
            )
            print(response)
            if hasattr(response, 'usage') and response.usage:
                print(f"Chunk {chunk_index+1} tokens: prompt={response.usage.prompt_tokens}, completion={response.usage.completion_tokens}")

            message = response.choices[0].message
            content = message.content or ""

            if not content:
                print(f"Warning: Model returned empty content (finish_reason: {response.choices[0].finish_reason})")
                raise ValueError("Model returned empty content")

            content = content.strip()

            if "```json" in content:
                content = content.split("```json")[1].split("```")[0].strip()
            elif "```" in content:
                content = content.split("```")[1].split("```")[0].strip()

            result = json.loads(content)
            return EmailAnalysis(**result)

        except Exception as e:
            print(f"LLM analysis error for chunk {chunk_index+1}: {e}")
            return self._fallback_analysis(emails)

    def _build_analysis_prompt(self, email_data: list[dict]) -> str:
        return f"""Analyze these {len(email_data)} emails received in the last 24 hours.

EMAILS:
{json.dumps(email_data, indent=2)}

TASKS:
1. Write a detailed 5-6 sentence summary covering:
   - Main topics and themes
   - Key senders and their purposes
   - Any notable patterns or trends
   - Important deadlines or time-sensitive items
   - Overall tone (promotional, informational, urgent, etc.)
2. Categorize each email as: work, personal, newsletters, promotions, notifications, or other
3. Identify which emails need a response (look for questions, meeting invites, action items)
4. Count how many are urgent (time-sensitive, from important senders, or have deadline mentions)

Return ONLY valid JSON with this structure:
{{
  "summary": "Detailed 5-6 sentence summary covering main topics, key senders, patterns, deadlines, and overall tone...",
  "categories": [
    {{"name": "work", "count": 5, "subjects": ["Subject 1", "Subject 2"]}},
    {{"name": "personal", "count": 2, "subjects": ["Subject 3"]}}
  ],
  "needs_response_ids": ["id1", "id2"],
  "urgent_count": 1
}}

Important:
- Only include email IDs in needs_response_ids if they clearly require user action
- List top 5 subjects per category
- Be conservative with "urgent" classification
- Make the summary detailed and informative (5-6 full sentences)"""

    def _fallback_analysis(self, emails: list) -> EmailAnalysis:
        """Fallback analysis if LLM fails"""
        # Simple keyword-based categorization
        categories_map = {
            "work": [],
            "newsletters": [],
            "promotions": [],
            "notifications": [],
            "personal": []
        }

        for email in emails:
            subject_lower = email.subject.lower()
            snippet_lower = email.snippet.lower()

            if any(word in subject_lower for word in ["unsubscribe", "newsletter"]):
                categories_map["newsletters"].append(email.subject)
            elif any(word in subject_lower for word in ["offer", "sale", "deal", "discount"]):
                categories_map["promotions"].append(email.subject)
            elif any(word in snippet_lower for word in ["notification", "alert", "reminder"]):
                categories_map["notifications"].append(email.subject)
            else:
                categories_map["personal"].append(email.subject)

        categories = [
            EmailCategory(name=name, count=len(subjects), subjects=subjects[:5])
            for name, subjects in categories_map.items()
            if subjects
        ]

        return EmailAnalysis(
            summary=f"Received {len(emails)} emails in the last 24 hours. Analysis temporarily unavailable.",
            categories=categories,
            needs_response_ids=[],
            urgent_count=0
        )
