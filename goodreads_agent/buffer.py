import os
from pathlib import Path

from dotenv import load_dotenv
from gql import Client, gql
from gql.transport.exceptions import TransportQueryError, TransportServerError
from gql.transport.requests import RequestsHTTPTransport
from requests.exceptions import RequestException

load_dotenv()
BUFFER_API_URL = os.getenv("BUFFER_API_URL", "https://api.buffer.com")
QUERY_DIRECTORY = Path(__file__).parent / "queries"
BuFFER_ACCESS_TOKEN = os.getenv("BUFFER_ACCESS_TOKEN")


def _load_query(filename: str):
    return gql((QUERY_DIRECTORY / filename).read_text(encoding="utf-8"))


def _create_client(buffer_token: str) -> Client:
    transport = RequestsHTTPTransport(
        url=BUFFER_API_URL,
        headers={"Authorization": f"Bearer {buffer_token}"},
        use_json=True,
        timeout=10,
    )
    return Client(transport=transport, fetch_schema_from_transport=False)


def _fetch_organizations(session) -> list[dict]:
    result = session.execute(_load_query("get_organizations.graphql"))
    account_data = result.get("account")
    if not account_data:
        print("[BUFFER GraphQL] No account data returned for this token.")
        return []
    return account_data.get("organizations", [])


def _fetch_channels(session, organization_id: str) -> list[dict]:
    result = session.execute(
        _load_query("get_channels.graphql"),
        variable_values={"input": {"organizationId": organization_id}},
    )
    return result.get("channels", [])


def _log_channel(channel: dict) -> None:
    print(
        f"[BUFFER] Found channel: {channel.get('name')} "
        f"({channel.get('service')}) -> ID: {channel.get('id')}"
    )


def get_user_channels(buffer_token: str) -> list[str]:
    """Fetch active channel IDs dynamically from Buffer."""
    client = _create_client(buffer_token)
    try:
        with client as session:
            channel_ids = []
            for organization in _fetch_organizations(session):
                for channel in _fetch_channels(session, organization["id"]):
                    if channel.get("isLocked"):
                        continue
                    _log_channel(channel)
                    channel_ids.append(channel["id"])
            return channel_ids
    except (TransportQueryError, TransportServerError) as error:
        print(f"[BUFFER GraphQL] Transport error while fetching channels: {error}")
        return []
    except RequestException as error:
        print(f"[BUFFER] Network error while fetching channels: {error}")
        return []


def _write_stub_post(social_media_post: str, image_url: str | None) -> dict:
    print("[STUB / BACKFILL MODE] Skipping live Buffer GraphQL API call.")
    output_file = "stubbed_social_posts.txt"
    try:
        with open(output_file, "a", encoding="utf-8") as file:
            file.write(f"--- Post ---\n{social_media_post}\nImage: {image_url}\n\n")
        print(f"[STUB] Appended post and image to local file: {output_file}")
    except OSError as error:
        print(f"[STUB] Failed to write to local file due to OS error: {error}")
    return {"buffer_status": "stubbed_success"}


def _get_channel_ids(buffer_token: str) -> list[str]:
    env_channel_ids = os.getenv("BUFFER_CHANNEL_IDS")
    if env_channel_ids:
        return [channel_id.strip() for channel_id in env_channel_ids.split(",") if channel_id.strip()]
    print("[BUFFER] Fetching channel IDs dynamically via gql...")
    return get_user_channels(buffer_token)


def _build_post_input(
    social_media_post: str,
    channel_id: str,
    image_url: str | None,
) -> dict:
    post_input = {
        "text": social_media_post,
        "channelId": channel_id,
        "schedulingType": "automatic",
        "mode": "addToQueue",
    }
    if image_url:
        post_input["assets"] = [{"image": {"url": image_url}}]
    return post_input


def _post_to_channel(session, mutation, channel_id: str, post_input: dict) -> bool:
    try:
        result = session.execute(mutation, variable_values={"input": post_input})
        data = result.get("createPost", {})
        if "message" in data:
            print(f"[BUFFER GraphQL] Mutation error on channel {channel_id}: {data['message']}")
            return False

        post_id = data.get("post", {}).get("id")
        print(f"[BUFFER GraphQL] Posted successfully to channel {channel_id}. Post ID: {post_id}")
        return True
    except (TransportQueryError, TransportServerError) as error:
        print(f"[BUFFER GraphQL] Transport error on channel {channel_id}: {error}")
    except RequestException as error:
        print(f"[BUFFER] Network error posting to channel {channel_id}: {error}")
    return False


def _post_to_channels(
    client: Client,
    channel_ids: list[str],
    social_media_post: str,
    image_url: str | None,
) -> int | None:
    mutation = _load_query("create_post.graphql")
    success_count = 0
    try:
        with client as session:
            for channel_id in channel_ids:
                post_input = _build_post_input(social_media_post, channel_id, image_url)
                if _post_to_channel(session, mutation, channel_id, post_input):
                    success_count += 1
    except RequestException as error:
        print(f"[BUFFER] Client connection error: {error}")
        return None
    return success_count


def post_to_buffer(social_media_post: str | None, image_url: str | None = None):
    """Post an update and optional image to all discovered Buffer channels."""
    if not social_media_post:
        print("No social media post content to send.")
        return {"buffer_status": "no_post_content"}

    buffer_token = os.getenv("BUFFER_ACCESS_TOKEN")
    if os.getenv("GOODREADS_BACKFILL") or not buffer_token:
        return _write_stub_post(social_media_post, image_url)

    channel_ids = _get_channel_ids(buffer_token)
    if not channel_ids:
        print("[BUFFER] No target channels found to post to.")
        return {"buffer_status": "no_channels_found"}

    success_count = _post_to_channels(
        _create_client(buffer_token),
        channel_ids,
        social_media_post,
        image_url,
    )
    if success_count is None:
        return {"buffer_status": "buffer_network_error"}
    if success_count > 0:
        return {"buffer_status": "posted_all"}
    return {"buffer_status": "buffer_all_failed"}
