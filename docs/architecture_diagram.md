# getAHint Architecture Diagram

```mermaid
flowchart TB
    User["User<br/>Guest or Logged-in"]
    ChatUI["Chat UI<br/>Static HTML/CSS/JS<br/>Bootstrap themed"]

    subgraph FastAPI["FastAPI Application"]
        Root["/ root<br/>Serves Chat UI"]

        subgraph Controllers["API Controllers"]
            EventAPI["Event Controller<br/>/eventService/ingestEvents<br/>/eventService/syncWebEvents"]
            ModelAPI["Model Controller<br/>/modelService/chat<br/>/modelService/trainEventModel"]
            AuthAPI["Auth Controller<br/>/auth/login<br/>/auth/register<br/>/auth/profile"]
        end

        subgraph Services["Service Layer"]
            EventService["Event Service<br/>Upsert events<br/>Normalize dates<br/>Assign categories"]
            WebIngest["Web Ingestion Service<br/>Configured sources/search sync"]
            ModelService["Model Service<br/>Intent routing<br/>Query orchestration"]
            VectorService["Vector Service<br/>Text search + embeddings<br/>Upcoming-date filtering"]
            CategoryService["Category Service<br/>Event category classifier"]
            Personalization["Personalization Service<br/>Profile preferences + interaction history"]
            AuthService["Auth Service<br/>Password hashing<br/>Session tokens"]
            AnswerService["Answer Generation Service<br/>Short answer + event cards"]
            Scheduler["Scheduler Service<br/>Periodic event refresh"]
        end
    end

    subgraph Storage["PostgreSQL Database"]
        Events[("events<br/>event details<br/>category<br/>vector embedding")]
        Users[("user_accounts<br/>user_sessions")]
        Profiles[("user_profiles<br/>user_preferences")]
        Interactions[("event_interactions<br/>views/clicks/saves")]
    end

    subgraph ML["ML / Retrieval Artifacts"]
        IntentModel["Intent Classifier<br/>TF-IDF + Logistic Regression"]
        CategoryModel["Category Classifier<br/>TF-IDF + Logistic Regression"]
        EmbeddingModel["Sentence Transformer<br/>all-MiniLM-L6-v2"]
        PgVector["pgvector / embedding_json<br/>Semantic similarity search"]
    end

    subgraph External["Optional External Sources"]
        ManualJSON["events.json<br/>Manual event data"]
        WebSources["Configured event URLs / search"]
    end

    User --> ChatUI
    ChatUI --> Root
    ChatUI --> ModelAPI
    ChatUI --> AuthAPI
    ChatUI --> EventAPI

    ManualJSON --> EventAPI
    WebSources --> WebIngest
    Scheduler --> WebIngest
    WebIngest --> EventService
    EventAPI --> EventService

    EventService --> CategoryService
    EventService --> Events
    EventService --> VectorService

    ModelAPI --> ModelService
    ModelService --> IntentModel
    ModelService --> VectorService
    ModelService --> Personalization
    ModelService --> AnswerService

    VectorService --> Events
    VectorService --> EmbeddingModel
    VectorService --> PgVector
    PgVector --> Events

    AuthAPI --> AuthService
    AuthService --> Users
    AuthAPI --> Profiles

    Personalization --> Profiles
    Personalization --> Interactions
    Personalization --> Events
    EventAPI --> Interactions

    CategoryService --> CategoryModel
```

## Project Flow

1. **User Access**
   - User opens the root URL.
   - The app first asks the user to choose Guest Mode or User Mode.
   - Guest users continue directly to chat.
   - User Mode requires login or registration, then loads profile preferences.

2. **Data Ingestion**
   - Admin ingests event data through `/eventService/ingestEvents`.
   - Events are normalized, categorized, and saved into PostgreSQL.
   - Optional web sync can refresh event data periodically through the scheduler.

3. **Training / Indexing**
   - `/modelService/trainEventModel` trains the intent classifier, trains the category classifier, categorizes existing events, and generates embeddings.
   - Event embeddings are stored in PostgreSQL using `pgvector` when available.

4. **Chat Query Processing**
   - The chat message is classified as greeting/help/feedback/event query.
   - Event queries use hybrid retrieval:
     - database text matching
     - vector similarity search
     - category matching
     - upcoming-date filtering

5. **Personalization**
   - Logged-in users can save profile preferences such as preferred categories.
   - The UI tracks event card views and "show details" interactions.
   - Recommendations are reranked using saved preferences and interaction history.

6. **Response Generation**
   - The backend returns a short answer summary and matching event records.
   - The UI displays results as compact cards.
   - Full event details appear only when the user clicks a card.

