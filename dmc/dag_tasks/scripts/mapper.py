import argparse
import json

import requests


def get_mapper(**kwargs):
    dojo_url = kwargs["dag_run"].conf.get("dojo_url")
    model_id = kwargs["dag_run"].conf.get("model_id")
    ofs = requests.get(f"{dojo_url}/dojo/outputfile/{model_id}").json()
    for of in ofs:
        mapper = of["transform"]
        with open(f'/mappers/mapper_{of["id"]}.json', "w") as f:
            f.write(json.dumps(mapper))


if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="mapper")
    parser.add_argument("kwargs", help="json string of arguments")
    args = parser.parse_args()
    get_mapper(**json.loads(args.kwargs))
