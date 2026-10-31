# System architecture

Planned architecture; implementation status is documented in the README.

```mermaid
flowchart TD
    subgraph ING["1. DATA INGESTION"]
        AQ["OpenAQ / CPCB<br/>Air quality"]
        WX["Open-Meteo<br/>Weather + mixing height"]
        FIRE["NASA FIRMS<br/>Fire detections"]
        OSM["OpenStreetMap<br/>Roads + land use"]
        BAN["Manual calendar<br/>Diwali + cracker bans"]
        CACHE["Local cache<br/>Source + timestamp"]
        AQ --> CACHE
        WX --> CACHE
        FIRE --> CACHE
        OSM --> CACHE
        BAN --> CACHE
    end
    subgraph FE["2. CLEANING & FEATURES"]
        CLEAN["Align units + times<br/>Handle gaps; flag sensor faults"]
        TIME["Lags + pre-event buildup"]
        VENT["Ventilation<br/>Wind x mixing height"]
        GEO["Road density + land use"]
        FEATURES["Inputs available at issue time"]
        CLEAN --> TIME
        CLEAN --> VENT
        CLEAN --> GEO
        TIME --> FEATURES
        VENT --> FEATURES
        GEO --> FEATURES
    end
    subgraph MOD["3. MODELS"]
        BASE["Baseline LightGBM<br/>Background PM2.5"]
        RES["Event residual targets<br/>Observed minus out-of-time baseline"]
        BURST["Diwali burst LightGBM<br/>Residual quantiles"]
        TOTAL["Combine baseline + burst"]
        SPACE["Spatial downscaling<br/>Ward estimates"]
        BASE --> RES
        RES -->|"Training targets"| BURST
        BASE --> TOTAL
        BURST --> TOTAL
        TOTAL --> SPACE
    end
    subgraph UNC["4. UNCERTAINTY"]
        RANGE["P10 / P50 / P90<br/>Calibrate total ranges"]
        CONF["Confidence indicator<br/>Coverage + freshness + holdout evidence"]
        RANGE --> CONF
    end
    subgraph ACT["5. ACTION LAYER"]
        WINDOWS["Lower-exposure windows<br/>No safe cracker-use claim"]
        HEALTH["School / health awareness"]
        PRIORITY["Officer ward priorities<br/>Human review"]
    end
    subgraph OUT["6. OUTPUT"]
        API["FastAPI"]
        DASH["Streamlit / Leaflet map<br/>Local geometry offline"]
        RESIDENT["Resident view"]
        OFFICER["Officer view"]
        API --> DASH
        DASH --> RESIDENT
        DASH --> OFFICER
    end
    subgraph VAL["7. VALIDATION"]
        SPLIT["Train through 2024<br/>Final test: Diwali 2025"]
        HOLD["Leave one station out"]
        PERSIST["Persistence baseline"]
        METRIC["MAE + RMSE + PM2.5 category accuracy<br/>Interval coverage + width"]
        SPLIT --> METRIC
        HOLD --> METRIC
        PERSIST --> METRIC
    end
    CACHE --> CLEAN
    FEATURES --> BASE
    FEATURES --> BURST
    FEATURES --> SPACE
    CLEAN -->|"Event observations: training only"| RES
    SPACE --> RANGE
    CONF --> WINDOWS
    CONF --> HEALTH
    CONF --> PRIORITY
    CONF --> API
    WINDOWS --> API
    HEALTH --> API
    PRIORITY --> API
    FEATURES -.-> SPLIT
    FEATURES -.-> HOLD
    CLEAN -.-> PERSIST
    SPACE -.->|"Held-out predictions"| METRIC
    METRIC -.->|"Earlier folds calibrate; 2025 only evaluates"| RANGE
    classDef ingestion fill:#DBEAFE,stroke:#2563EB,color:#172554;
    classDef features fill:#FEF3C7,stroke:#D97706,color:#451A03;
    classDef models fill:#EDE9FE,stroke:#7C3AED,color:#2E1065;
    classDef uncertainty fill:#FCE7F3,stroke:#DB2777,color:#500724;
    classDef actions fill:#DCFCE7,stroke:#16A34A,color:#052E16;
    classDef output fill:#CFFAFE,stroke:#0891B2,color:#083344;
    classDef validation fill:#F1F5F9,stroke:#475569,color:#0F172A;
    class AQ,WX,FIRE,OSM,BAN,CACHE ingestion;
    class CLEAN,TIME,VENT,GEO,FEATURES features;
    class BASE,RES,BURST,TOTAL,SPACE models;
    class RANGE,CONF uncertainty;
    class WINDOWS,HEALTH,PRIORITY actions;
    class API,DASH,RESIDENT,OFFICER output;
    class SPLIT,HOLD,PERSIST,METRIC validation;
```

## Mentor walkthrough

1. Collect pollution, weather, fires, map features, and policy dates; cache inputs for offline use.
2. Clean records and calculate recent pollution buildup, ventilation, and spatial context.
3. Predict background pollution and an additional event-associated residual, then estimate ward conditions.
4. Attach uncertainty and data-quality indicators before producing guidance and officer priorities.
5. Serve resident and officer views; compare held-out forecasts against persistence.

## Pitch slide: 10 boxes

```mermaid
flowchart LR
    subgraph ING["INGESTION"]
        DATA["Air + weather + fires<br/>OSM + festival calendar"]
    end
    subgraph FE["FEATURES"]
        FEATURES["Clean + lags + ventilation<br/>Buildup + spatial context"]
    end
    subgraph MOD["MODELS"]
        BASE["Baseline LightGBM"]
        BURST["Diwali residual quantiles"]
        WARDS["Combine + estimate wards"]
    end
    subgraph UNC["UNCERTAINTY"]
        RANGE["P10 / P50 / P90<br/>Calibrate + report confidence"]
    end
    subgraph ACT["ACTIONS"]
        ACTION["Exposure windows<br/>Advisories + priorities"]
    end
    subgraph OUT["OUTPUT"]
        API["FastAPI"]
        DASH["Dashboard<br/>Resident + Officer"]
    end
    subgraph VAL["VALIDATION"]
        TEST["Time split + station holdout<br/>Compare persistence"]
    end
    DATA --> FEATURES
    FEATURES --> BASE
    FEATURES --> BURST
    BASE -->|"Out-of-time residuals for training"| BURST
    BASE --> WARDS
    BURST --> WARDS
    FEATURES --> WARDS
    WARDS --> RANGE
    RANGE --> ACTION
    RANGE --> API
    ACTION --> API
    API --> DASH
    FEATURES -.-> TEST
    WARDS -.-> TEST
    classDef ingestion fill:#DBEAFE,stroke:#2563EB,color:#172554;
    classDef features fill:#FEF3C7,stroke:#D97706,color:#451A03;
    classDef models fill:#EDE9FE,stroke:#7C3AED,color:#2E1065;
    classDef uncertainty fill:#FCE7F3,stroke:#DB2777,color:#500724;
    classDef actions fill:#DCFCE7,stroke:#16A34A,color:#052E16;
    classDef output fill:#CFFAFE,stroke:#0891B2,color:#083344;
    classDef validation fill:#F1F5F9,stroke:#475569,color:#0F172A;
    class DATA ingestion;
    class FEATURES features;
    class BASE,BURST,WARDS models;
    class RANGE uncertainty;
    class ACTION actions;
    class API,DASH output;
    class TEST validation;
```

Ward values are estimates, not measurements. Burst residuals are not causal source attribution. Quantile coverage and spatial uncertainty require validation. Results: [TO BE MEASURED].
