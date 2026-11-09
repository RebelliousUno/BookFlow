
import asyncio
import os
from pathlib import Path

from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.httpx import HTTPXAsyncTransport

from goodreads_agent.hardcover_activities_models import (
    ActivityItem,
    HardcoverActivityResponse,
)

load_dotenv()
    
async def get_activites(last_run_time: str = "2024-06-01T00:00:00Z") -> list[ActivityItem]:
    """
    Fetches activities from the Hardcover API since the last run time.
    
    args:
        last_run_time (str): The timestamp of the last run in ISO 8601 format. Defaults to "2024-06-01T00:00:00Z".

        returns:
        list[ActivityItem]: A list of ActivityItem objects representing the activities fetched from the API
    """
    api_key = os.getenv("HARDCOVER_APP_API_KEY")
    api_url = os.getenv("HARDCOVER_APP_API_URL")

    if not api_key:
        raise ValueError("HARDCOVER_APP_API_KEY is not set in the environment variables.")

    if not api_url:
        raise ValueError("HARDCOVER_APP_API_URL is not set in the environment variables.")

    transport = HTTPXAsyncTransport(
    url=api_url,
    headers={"Authorization": f"Bearer {api_key}"},
   )

    client = Client(transport=transport, fetch_schema_from_transport=False)
    query_path = Path(__file__).parent / "queries" / "get_activities.graphql"
    
    query = gql(query_path.read_text(encoding="utf-8"))
    async with client as session:
        result = await session.execute(query, variable_values={"lastRunTime":last_run_time})
        # Assuming 'result' is the dictionary returned by session.execute()
    validated_data = HardcoverActivityResponse.model_validate(result)

    for activity in validated_data.activities:
        print(f"Activity {activity}")
        print(f"Event: {activity.event} | Book: {activity.book.title}")
        if activity.book.book_series:
            series = activity.book.book_series[0]
            print(f"Series: {series.series.name} (#{series.position})")
    return validated_data.activities


def main():
    asyncio.run(get_activites())


if __name__ == "__main__":
    main()  