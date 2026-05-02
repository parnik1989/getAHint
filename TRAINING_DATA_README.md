# Training Data for Hyderabad Events Model

## Overview
This training data collection includes comprehensive information about Hyderabad events, festivals, and user intents to train your event search and classification models.

## Files Created

### 1. `hyderabad_events_2025.json`
- **Format**: JSON array with event objects
- **Records**: 20 major events in Hyderabad for 2025
- **Fields**: 
  - event_id: Unique identifier
  - event_name: Name of the event
  - event_description: Detailed description (semantic text for similarity matching)
  - event_date: Event date (YYYY-MM-DD format)
  - event_address: Location/venue
  - event_category: Type of event (Cultural Festival, Sports, Food & Culinary, etc.)
  - event_type: Category type (festival, celebration, sports, concert, tour, exhibition, conference)

- **Events Included**:
  - Religious/Cultural: Ganesh Chaturthi, Bonalu, Diwali, Eid ul-Fitr, Eid al-Adha
  - Food & Culinary: Biryani Festival, Foodie Festival
  - Arts & Culture: Literary Festival, Film Festival, Music Concerts, Golconda Festival
  - Sports: Sailing Week, Deccan Derby, Marathon
  - Heritage: Charminar Heritage Walk, Museum Exhibitions
  - National: Telangana Formation Day, Independence Day
  - Business: Tech Summit, Numaish Exhibition

### 2. `hyderabad_events_guide.txt`
- **Format**: Structured text file
- **Content**: Detailed descriptions of events with dates, locations, and visitor information
- **Purpose**: Reference guide for event details and Hyderabad tourism tips

### 3. Enhanced Intent Training Data (in `modelService.py`)
- **Total Intents**: ~45+ training examples
- **Intent Categories**:
  - greeting: "hi", "hello", "hey", "good morning"
  - help: "help me", "what can you do", "assist me"
  - event_query: Various event and festival related queries
  - farewell: "goodbye", "bye", "thank you"

- **Event-Specific Queries**:
  - General: "what festivals are coming", "events happening near me"
  - Specific festivals: "ganesh chaturthi", "bonalu festival", "diwali"
  - Event types: "concerts", "art exhibitions", "heritage tours", "food festivals"
  - Time-based: "events this week", "upcoming celebrations"

## How to Use This Data

### Step 1: Train the Intent Model
The enhanced intent training data is automatically used when you call:
```python
trainEventModelService("hyderabad")
```
This will:
- Train the intent classifier on 45+ labeled examples
- Train the event similarity model on 20 Hyderabad events
- Save both models to `app/ml/`

### Step 2: Test with Sample Queries
Example queries that should work well with your model:
```python
# General queries
"show me upcoming festivals"
"what events are happening in Hyderabad"
"tell me about cultural celebrations"

# Specific events
"when is bonalu festival"
"ganesh chaturthi events"
"biryani festival details"

# Time-based
"events this month"
"celebrations coming soon"
```

### Step 3: Extend with More Data
To add more events or intents:
1. Add new events to `hyderabad_events_2025.json`
2. Add new training examples to the `training_data` list in `intent_train_model()`
3. Retrain the model by calling `trainEventModelService()` again

## Data Statistics

- **Total Events**: 20
- **Intent Training Examples**: 45+
- **Festival Types**: 6 (Religious, Food, Arts, Sports, Heritage, National)
- **Event Coverage**: Jan-Dec 2025

## Semantic Similarity Coverage

The semantic model now understands:
- Event names and descriptions
- Festival terminology and names
- Cultural and religious event references
- Location and venue information
- Event categories and types

This allows matching user queries like:
- "Tell me about traditional celebrations" → Bonalu, Ganesh Chaturthi, Diwali
- "Food festivals in the city" → Biryani Festival, Foodie Festival
- "Sports events near Hussain Sagar" → Sailing Week
- "Heritage walks" → Charminar Heritage Walk

## Next Steps

1. **Retrain your model** with the new data
2. **Test with various user queries** to validate semantic matching
3. **Add more events** as the year progresses
4. **Collect real user queries** to improve intent classification
5. **Consider adding ratings/popularity** to events for ranking results

## Files Location

All training files are in:
```
app/data/json/
├── hyderabad_events_2025.json      (20 Hyderabad events)
└── hyderabad_events_guide.txt       (Detailed event guide)
```

Model files after training will be in:
```
app/ml/
├── eventModel.pkl                  (Event similarity model with embeddings)
└── intentModel.pkl                 (Intent classification model)
```
