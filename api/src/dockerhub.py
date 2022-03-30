"""
    Docker Hub helper to scrape phantom images.
    see https://docs.docker.com/docker-hub/api/latest/#
    see https://github.com/jataware/dojo/issues/77
    Requires credentials for Pro or Team plan.
"""
import logging
import requests
from uuid import UUID
from elasticsearch import Elasticsearch
from elasticsearch.exceptions import NotFoundError

from src.settings import settings

es = Elasticsearch([settings.ELASTICSEARCH_URL], port=settings.ELASTICSEARCH_PORT)

logger: logging.Logger = logging.getLogger(__name__)


def is_uuid(uuid_str):
    """
    Simple way to check to see if a string is a valid UUID.
    Try to build a UUID object and catch if it fails
    """
    try:
        UUID("{%s}" % uuid_str)
        return True
    except ValueError as e:
        return False


def authenticate() -> str:
    """
    Description
    -----------
    Basic authentication of Docker Hub Api. Uses base url and credentials
    stored in .env settings.

    Returns
    -------
    str: JWT Token
    """

    url = f"{settings.DOCKERHUB_URL}/users/login"
    dockerhub_user = settings.DOCKERHUB_USER
    dockerhub_pwd = settings.DOCKERHUB_PWD
    auth_body = {"username": dockerhub_user, "password": dockerhub_pwd}

    response = requests.post(
        url, json=auth_body, headers={"Content-Type": "application/json"}
    )
    resp_json = response.json()

    if "token" in resp_json:
        return resp_json["token"]
    else:
        logger.error(
            f"Could not authenticate {url} with user {dockerhub_user}: {resp_json}"
        )
        raise


def get_image_tags(repo):
    """
    Description
    -----------
    Called by phantom.py get_base_images() to scrape DockerHub for
    Jataware/dojo-publish images.

    Returns
    -------
    JSON Array of
        {
            "sort_order": int,
            "display_name": "string",
            "image": "string"
        }

    """

    auth_token = authenticate()

    """
        Docker Hub Url options for Get details of repository's images:
            page_size: Number of images to get per page. Defaults to 10. Max of 100.
            status: "active", "inactive"; Filters to only show images of this status.
            currently_tagged: boolean; Filters to only show images with:
                true: at least 1 current tag.
                false: no current tags.
            ordering: "last_activity""-last_activity""digest""-digest": Orders the results by this property.
            Prefixing with - sorts by descending order.
    """

    url = (
        f"{settings.DOCKERHUB_URL}/"
        f"repositories/{settings.DOCKERHUB_ORG}/"
        f"{repo}/tags?page_size=100"
    )

    headers = {"Accept": "application/json", "Authorization": f"Bearer {auth_token}"}

    # Get list of image tag dicts.
    image_tags = get_repo_image_details(url, headers, [], repo)

    model_images = [
        image_tag.get("display_name")
        for image_tag in image_tags
        if is_uuid(image_tag.get("display_name"))
    ]

    models = es.mget(index="models", body={"ids": model_images})

    model_index = {
        model_obj["_id"]: model_obj.get("_source", {})
        for model_obj in models.get("docs", [])
    }

    curated_tags = []
    for image_tag in image_tags:
        tag_name = image_tag["display_name"]
        if tag_name in model_index:
            model_obj = model_index[tag_name]
            # Skip images that look like a uuid, but don't have a model associated
            if not model_obj:
                continue
            # Skip images that are not the most recent version
            if model_obj.get("next_version", False) is not None:
                continue
            image_tag["display_name"] = f"{model_obj['name']} ({tag_name})"
        curated_tags.append(image_tag)

    curated_tags.sort(
        key=lambda item: (
            not item.get("display_name").startswith("Ubuntu"),
            item.get("display_name"),
        )
    )

    # Enumerate and set sort_order; although, Phantom does not seem to use this.
    for idx, d in enumerate(curated_tags):
        d["sort_order"] = idx

    return curated_tags


def get_repo_image_details(url: str, headers: dict, image_tags, repo: str) -> list:
    """
    Description
    -----------
    GET request at Docker Hub to Get details of repository's images.

    Parameters
    ----------
    url: str
        Constructed url for GET.
    headers: dict
        Authentication headers.
    image_tags: list
        Current list of dict of image tag info.

    Returns
    -------
    Dict of display_name: image

    Notes
    -----
    This is built to be recursive because DockerHub will paginate the response;
    therefore, make another call if the "next" url is returned.
    """

    try:
        response = requests.get(url, headers=headers)
        resp = response.json()

        """
        Example Response
        ----------------
            {
            "count": 79,
            "next": "https://hub.docker.com/v2/jataware/dojo-publish/tags?page=2",
            "previous": null,
            "results": [
                {
                    'creator': 13929046, 
                    'id': 200325956, 
                    'image_id': None, 
                    'images': [
                        {
                            'architecture': 'amd64', 
                            'features': '', 
                            'variant': None, 
                            'digest': 'sha256:b991dcdf746cfd92471dcd3dcacc78d1d1e6a9e3397c26da9d5b552ad6ba11ff', 
                            'os': 'linux', 
                            'os_features': '', 
                            'os_version': None, 
                            'size': 8769398376, 
                            'status': 'active', 
                            'last_pulled': None, 
                            'last_pushed': '2022-03-30T14:17:02.184254Z'
                        }
                    ], 
                    'last_updated': '2022-03-30T14:17:02.313327Z', 
                    'last_updater': 13929046, 
                    'last_updater_username': 'automationjat', 
                    'name': '0259da01-e085-4dfc-b432-17c23c14d569', 
                    'repository': 14874028, 
                    'full_size': 8769398376, 
                    'v2': True, 
                    'tag_status': 'active', 
                    'tag_last_pulled': None, 
                    'tag_last_pushed': '2022-03-30T14:17:02.313327Z'
                },
            ...
        """
        if "results" in resp:
            for result in resp["results"]:
                updated_at = result["tag_last_pushed"]
                tag = result['name']
                image = f"{settings.DOCKERHUB_ORG}/{repo}-publish:{tag}"
                display_name=tag.replace("-latest", "")
                image_tags.append({
                    "display_name": display_name,
                    "image": image,
                    "sort_order": 0,
                    "updated_at": updated_at,
                })

        # Get the next page if there is a "next".
        if "next" in resp and resp["next"] is not None:
            image_tags = get_repo_image_details(resp["next"], headers, image_tags, repo)

        return image_tags

    except Exception as e:
        logger.error(e.message, e.args)
        return ""
