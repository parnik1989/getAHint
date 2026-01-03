import os
from fastapi import FastAPI
from contextlib import asynccontextmanager
from app.controllers import eventController, modelController, telegramController
from sklearn.pipeline import Pipeline
from sklearn.feature_extraction.text import CountVectorizer
from sklearn.linear_model import LogisticRegression 
from app.services.modelService import train_model,intent_train_model
import joblib

app = FastAPI(title="getAHintService")

app.include_router(eventController.router, prefix="/eventService")
app.include_router(modelController.router, prefix="/modelService")
app.include_router(telegramController.router, prefix="/telegramService")


