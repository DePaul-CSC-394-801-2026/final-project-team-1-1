import os
import json
from datetime import timedelta

from openai import OpenAI
from apify_client import ApifyClient
from django.core.management.base import BaseCommand
from pages.models import DIYProject, ProjectStep


class Command(BaseCommand):
    def handle(self, *args, **options):
        client = ApifyClient(os.getenv("APIFY_CRAWLER_KEY")) # THESE ARE CURRENTLY MY KEYS - james
        openai_client = OpenAI(api_key=os.getenv("OPENAI_KEY")) # THESE ARE CURRENTLY MY KEYS - james

        test_url = "https://www.familyhandyman.com/project/dining-table-leaf/"

        crawlerRun = client.actor("apify/website-content-crawler").call(run_input={
            "startUrls": [{"url": test_url}],
            "maxCrawlPages": 1,
        })


        items = client.dataset(crawlerRun["defaultDatasetId"]).list_items().items
        if not items:
            self.stdout.write(self.style.ERROR("no data :("))
            return

        page_text = items[0].get("text", "")
        self.stdout.write(f"Scraped {len(page_text)} chars. Sending to OpenAI...")

        response = openai_client.chat.completions.create(
            model="gpt-4o-mini",
            messages=[
                        {
                            #set the behaviour/boundaries
                            "role": "system",
                            "content": (
                                "You extract structured data from DIY project pages!!! "
                                "Use ONLY the text provided or else.... Do NOT invent anything. "
                                "OUTPUT RAW JSON ONLY. NO MARKDOWN. NO EXPLANATION."
                            )
                        },
                        {
                            # The user role represents tasks/requests from the user!
                            "role": "user",
                            "content": f"""Extract the following from this DIY page's text and return as JSON:
        
                                {{
                                  "title": "string",
                                  "description": "string",
                                  "avg_price": float or null,
                                  "step_count": integer,
                                  "estimated_time_minutes": integer or null,
                                  "is_rental_safe": boolean,
                                  "materials_json": ["string"],
                                  "tools_json": ["string"],
                                  "steps": [
                                    {{"step_number": integer, "instruction_text": "string"}}
                                  ]
                                }}
                
                                Rental Safe Rule: is_rental_safe = false if a drill is required or holes are drilled.
                                If a value is not present in the text, use null.
                                
                                page's text:
                            {page_text}"""
                        }
            ]
        )

        #
        raw = response.choices[0].message.content

        # convert json object into python dict
        ai_data = json.loads(raw)

        # the result kept fucking up the total count. This is to try and fix
        ai_data["step_count"] = len(ai_data.get("steps", []))

        self.stdout.write(self.style.SUCCESS(f"WE GOT IT!!!!!! - {ai_data.get('title')}"))

        # Take the data that the ai formatted and create a new project from it
        project = DIYProject.objects.create(
            title=ai_data.get("title", "Untitled"),
            description=ai_data.get("description", ""),
            avg_price=ai_data.get("avg_price"),
            step_count=ai_data["step_count"],
            estimated_time=ai_data.get("estimated_time_minutes") if ai_data.get("estimated_time_minutes") else timedelta(0), # should probably remove time if it's 0, when displayed
            is_rental_safe=ai_data.get("is_rental_safe", False), # Is my logic right? lol
            requires_drilling=not ai_data.get("is_rental_safe", True),
            materials_json=ai_data.get("materials_json", []),
            tools_json=ai_data.get("tools_json", []),
        )

        # Have to iterate through each step fetched by the ai to attach it to the related project
        for step in ai_data.get("steps", []):
            ProjectStep.objects.create(
                project=project,
                step_number=step["step_number"],
                instruction_text=step["instruction_text"],
            )

        self.stdout.write(self.style.SUCCESS(f"{project.title} is now in the db... :)!!!!!"))