import re
from typing import List, Optional
from pydantic import BaseModel, EmailStr, Field
from fastapi import APIRouter, Depends, Body, Path
from fastapi.encoders import jsonable_encoder
from app.auth import UserAuth
from app.session import Session
from app.utils import get_tag_names, AllOptional
from app.core.mongo import DB

recipe_db = DB('recipes')

tags = [
    {
        'name': 'recipes',
        'description': 'Manage recipes'
    }
]

router = APIRouter(prefix='/recipes', tags=get_tag_names(tags),
                   dependencies=[Depends(UserAuth.require_authorization)])


# class RecipeIngredientSchema(BaseModel):
#     name: str = Field(description='The ingredient name')

# class RecipeToolSchema(BaseModel):
#     name: str = Field(description='The ingredient tool')

# class RecipeInstructionsSchema(BaseModel):
#     name: str = Field(description='The ingredient instructions')

class RecipeSchema(BaseModel):
    name: str = Field(None, description='The recipe name')
    ingredients: List[str] = Field(None, description='The recipe ingredients')
    tools: List[str] = Field(None, description='The recipe tools')
    instructions: List[str] = Field(None, description='The recipe instructions')
    # id: str = Field(None, description='The recipe id')
    # title: str = Field(description='The recipe title')
    # desc: str = Field(None, description='The recipe title')
    # text: str = Field(None, description='The recipe text')
    # steps: Optional[List[RecipeStepSchema]] = Field([], description='The list of steps')

    # class Config:
    #     schema_extra = {
    #         "example": {
    #             'id': 'grilled_cheese',
    #             'title': 'Grilled Cheese',
    #             'steps': [
    #                 {'text': 'place bread on place', 'verb': 'place', 'noun': 'bread'},
    #                 {'text': 'place cheese on bread', 'verb': 'place', 'noun': 'cheese'},
    #                 {'text': 'make the rest of the sandwich'},
    #             ],
    #         }
    #     }

class PartialRecipeSchema(RecipeSchema, metaclass=AllOptional):
    pass


PARAM_RECIPE_ID = Path(None, alias='recipe_id', description='The recipe UID')


@router.get("/", response_description="Get all recipes")
async def get_all():
    return await recipe_db.get_all()

@router.get("/q", response_description="Search recipes.")
async def search_recipes(query: PartialRecipeSchema = Depends()):
    return await recipe_db.get(**query.dict())

@router.get("/{recipe_id}", response_description="Get a specific recipe")
async def get_data(id: str = PARAM_RECIPE_ID):
    return await recipe_db.get(id)

@router.post("/", response_description="Add a recipe")
async def add_recipe(data: RecipeSchema = Body(...)):
    # if not data.id and data.title:
    #     data.id = str2id(data.title)
    return await recipe_db.add(data.dict())

@router.put("/{recipe_id}", response_description="Update a recipe")
async def update_data(id: str = PARAM_RECIPE_ID, data: PartialRecipeSchema = Body(...)):
    return await recipe_db.update(id, {
        k: v for k, v in data.dict().items() 
        if v is not None
    })

@router.delete("/{recipe_id}", response_description="Delete a recipe")
async def delete_data(id: str = PARAM_RECIPE_ID):
    return await recipe_db.delete(id)

def str2id(txt):
    return re.sub(r'\W+', '', txt.replace(' ', '_')).lower()
