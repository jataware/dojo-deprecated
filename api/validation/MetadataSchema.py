from typing import Optional, List, Dict, Any
from enum import Enum
from pydantic import BaseModel, Field

from validation import SpacetagSchema

# Metadata Model Used to store annotation data along with any other metadata we may need inside of a dictionary with string keys and any type of data.


class MetaModel(BaseModel):
    metadata: Dict[str, Any] = {}
    annotations: Optional[SpacetagSchema.SpaceModel]
