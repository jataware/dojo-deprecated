"""
    Docker Hub helper to scrape phantom images.
    see https://docs.docker.com/docker-hub/api/latest/#
    see https://github.com/jataware/dojo/issues/77
    Requires credentials for Pro or Team plan.
"""
import json
from logging import Logger
import logging
import os
import requests

logger: Logger = logging.getLogger(__name__)


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

    url = f'{os.getenv("DOCKERHUB_URL")}/users/login'
    dockerhub_user = os.getenv("DOCKERHUB_USER")
    dockerhub_pwd = os.getenv("DOCKERHUB_PWD")
    auth_body = {"username": dockerhub_user, "password": dockerhub_pwd}

    response = requests.post(url, json = auth_body, headers = {'Content-Type':'application/json'})
    resp_json = response.json()

    if 'token' in resp_json:
        return resp_json['token']
    else:
        logger.error(f"Could not authenticate {url} with user {dockerhub_user}: {resp_json}")
        return None


def get_image_tags():
    """
        Description
        -----------
        Called by phantom.py get_base_images() to scrape DockerHub for
        Jataware/dojo-publish images.

        Returns
        -------
        JSON Array of
            {
                "sort_order": 0,
                "display_name": "string",
                "image": "string"
            }

    """

    auth_token = authenticate()
    if not auth_token:
        return "" # authenticate() above will log the error

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

    url = f'{os.getenv("DOCKERHUB_URL")}/namespaces/jataware/repositories/dojo-publish/images?status=active&ordering=last_activity&currently_tagged=true&page_size=100'
    headers = {"Accept" :"application/json", "Authorization": f"Bearer {auth_token}"}

    return get_repo_image_details(url, headers)


def get_repo_image_details(url: str, headers: dict, image_tags: list = [], sort_order: int = 0):
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
            Current list of image tag info.
        sort_order: int
            Current sort_order.

        Returns
        -------
        List of image tag info:
            {
                "sort_order": 0,
                "display_name": "string",
                "image": "string"
            }

        Notes
        -----
        This is built to be recursive because DockerHub will paginate the response;
        therefore, make another call if the "next" url is returned.
    """

    try:
        response = requests.get(url, headers = headers)
        resp = response.json()

        """
        Example Response
        ----------------
            {
            "count": 79,
            "next": "https://hub.docker.com/v2/namespaces/jataware/repositories/dojo-publish/images?page=2&status=active",
            "previous": null,
            "results": [
                {
                    "namespace": "jataware",
                    "repository": "dojo-publish",
                    "digest": "sha256:81ae08c9a8093e0c0c10313b844aa70e1f5be6c582b1c1a41fc073a37df35528",
                    "tags": [
                        {
                            "tag": "GoogleTrends-latest",
                            "is_current": true
                        }
                    ],
                    "last_pushed": "2021-07-15T01:16:32.454626Z",
                    "last_pulled": "2021-07-21T14:58:42.765245Z",
                    "status": "active"
                },
            ...
        """
        if "results" in resp:
            for r in resp["results"]:
                if "tags" in r:
                    tags = r["tags"][0]
                    tag = tags["tag"]
                    image = r["namespace"] + "/" + r["repository"] + "/" + tag
                    display_name = tag.replace('-latest','')

                    image_tags.append( {"sort_order":sort_order, "image":image, "display_name": display_name} )
                    sort_order += 1

        # Get the next page if there is a "next".
        if "next" in resp and resp["next"] != None:
            image_tags = get_repo_image_details(resp["next"], headers, image_tags, sort_order)

        return image_tags

    except Exception as e:
        logger.error(e.message, e.args)
        return ""