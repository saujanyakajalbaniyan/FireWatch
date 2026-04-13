import zlib
import base64
import urllib.request
import os

diagrams = {
    'architecture': 'graph TD;\n    subgraph Data Sources\n        A1[Live Surveillance Camera Feeds]\n        A2[NASA FIRMS API Satellite Data]\n    end\n\n    subgraph Backend System\n        B1[Video Stream Ingestion]\n        B2[AI Inference YOLOv8 + CNN+LSTM]\n        B3[NASA Data Fetcher]\n        \n        B1 --> |Frames| B2\n        B2 -->|Confidence Score| C1{Fire Detected?}\n        B3 --> |Thermal Spots| C2[Geospatial Analyzer]\n    end\n\n    subgraph Frontend and Notifications\n        D1[React Dashboard UI]\n        D2[SMS & Email Alerts]\n        D3[Emergency Webhooks]\n    end\n\n    A1 --> B1\n    A2 --> B3\n    C1 -- Yes --> E[Event Trigger]\n    C2 --> E\n    E -->|WebSocket| D1\n    E -->|API Request| D2\n    E -->|HTTP POST| D3',
    'use_case': 'flowchart LR\n    User[Dispatcher]\n    System[AI Detection System]\n    FIRMS[NASA FIRMS API]\n    Camera[Surveillance Camera]\n    Responder[Emergency Responder]\n\n    User -->|View Live Map Dashboard| System\n    User -->|Configure Notification Alerts| System\n    System -->|Fetch Thermal Hotspots| FIRMS\n    Camera -->|Send Video Stream| System\n    System -->|Trigger SMS/Email/Voice| Responder\n    System -->|WebSocket Real-time Updates| User',
    'class': 'classDiagram\n    class VideoProcessor {\n        +process_frame(frame)\n        +detect_fire_yolo(frame)\n        +validate_temporal_lstm(seq)\n        -confidence_score: float\n    }\n    class NASAFirmsAPI {\n        +api_key\n        +poll_recent_hotspots(lat, lon)\n    }\n    class NotificationManager {\n        +send_sms(number, message)\n        +send_email(email, payload)\n    }\n    class EventStore {\n        +log_detection_event(data)\n    }\n    class DashboardServer {\n        +app: Flask\n        +emit_live_data()\n    }\n    VideoProcessor --> EventStore : Logs detections\n    NASAFirmsAPI --> EventStore : Logs hotspots\n    EventStore --> DashboardServer : Feeds data\n    DashboardServer --> NotificationManager : Triggers alerts',
    'activity': 'stateDiagram-v2\n    [*] --> IngestData\n    state IngestData {\n        FetchVideo: Receive Video Frames\n        FetchNASA: Request NASA FIRMS API\n    }\n    FetchVideo --> AI_Analysis\n    FetchNASA --> Geospatial_Mapping\n    \n    state AI_Analysis {\n        YOLO_Box: Bounding Box YOLOv8\n        CNN_LSTM: Temporal Sequence Check LSTM\n    }\n    \n    AI_Analysis --> Decision\n    Decision --> LogEvent : Confidence > 80%\n    Decision --> FetchVideo : Confidence < 80%\n    \n    LogEvent --> TriggerAlerts\n    Geospatial_Mapping --> TriggerAlerts : New Spot Detected\n    \n    state TriggerAlerts {\n        SendSMS: Dispatch SMS & Email Alerts\n        UpdateUI: Update React Dashboard\n    }\n    \n    TriggerAlerts --> [*]',
    'sequence': 'sequenceDiagram\n    participant Cam as Camera\n    participant FIRMS as NASA FIRMS\n    participant Back as Backend Flask\n    participant AI as AI Model\n    participant UI as React UI\n    participant Comm as Twilio/Email\n\n    Cam->>Back: Continuous video frames\n    Back->>AI: Pass frame for analysis\n    AI-->>Back: Fire confidence score\n    \n    Back->>FIRMS: Poll thermal anomaly data\n    FIRMS-->>Back: Return JSON thermal data\n\n    alt Fire Confidence > Threshold\n        Back->>UI: WebSocket Trigger Data\n        Back->>Comm: Send Alert Payload\n        Comm->>User: Deliver SMS/Email\n    end',
    'database': 'erDiagram\n    DETECTION_EVENT {\n        string event_id PK\n        float confidence\n        string timestamp\n    }\n    NASA_HOTSPOT {\n        string hotspot_id PK\n        float latitude\n        float longitude\n        string acq_time\n    }\n    USER_PREFERENCE {\n        string admin_id PK\n        string alert_email\n        string alert_phone\n    }\n    DETECTION_EVENT ||--o{ NASA_HOTSPOT : belongs_to\n    USER_PREFERENCE ||--o{ DETECTION_EVENT : receives'
}

os.makedirs('diagrams', exist_ok=True)

for name, code in diagrams.items():
    compressed = zlib.compress(code.encode('utf-8'), 9)
    b64 = base64.urlsafe_b64encode(compressed).decode('utf-8').rstrip('=')
    url = f'https://kroki.io/mermaid/png/{b64}'
    
    req = urllib.request.Request(url, headers={'User-Agent': 'Mozilla/5.0'})
    try:
        with urllib.request.urlopen(req) as response, open(f'diagrams/{name}.png', 'wb') as out_file:
            data = response.read()
            out_file.write(data)
            print(f'Downloaded: {name}.png')
    except Exception as e:
        print(f'Error downloading {name}: {e}')
