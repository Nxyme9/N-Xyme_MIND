# N-Xyme MIND System Architecture Diagrams

This document contains Mermaid diagrams illustrating the core architecture of the N-Xyme MIND system.

---

## 1. System Overview

```mermaid
flowchart LR
    subgraph External
        direction LR
        OpenCode[OpenCode Platform]
        MCP[MCP Servers]
        MultiAgent[Multi-agent Frameworks]
    end

    subgraph Core_System
        direction LR
        
        subgraph Orchestration
            O[Orchestration Layer]
        end
        
        subgraph Intelligence
            I[Intelligence Layer]
        end
        
        subgraph Memory_Core
            M[Memory Core]
        end
        
        subgraph Learning
            L[Learning Engine]
        end
        
        subgraph Infrastructure
            IF[Infrastructure]
        end
        
        subgraph Local_LLM
            LLM[Local LLM]
        end
        
        subgraph Data
            D[Data Layer]
        end
    end

    External -->|Integrates| O
    O --> I
    I --> M
    M --> L
    L --> IF
    IF --> LLM
    LLM --> D
    
    M <--> L
    I <--> L
    IF <--> D
    
    style External fill:#f9f,stroke:#333,stroke-width:2px
    style Core_System fill:#bbf,stroke:#333,stroke-width:2px
```

---

## 2. Orchestration Layer

```mermaid
flowchart TB
    subgraph Orchestration_Layer
        direction TB
        
        AL[Agent Loop] --> TR[Triggers]
        TR --> WF[Workflows]
        WF --> GV[Governance]
        GV --> SN[Sessions]
        SN --> TS[Tasks]
        
        BMAD[BMAD Integration] -.-> WF
        BMAD -.-> GV
    end

    subgraph Triggers
        T1[Pattern Matching]
        T2[Memory Augmentation]
        T3[Predictive]
        T4[Learning-based]
        T5[Keyword Fallback]
        
        TR --> T1
        TR --> T2
        TR --> T3
        TR --> T4
        TR --> T5
    end

    subgraph Workflows
        W1[bmad-resilience]
        W2[bmad-memory]
        W3[bmad-catalyst-chain]
        W4[bmad-validate-prd]
        
        WF --> W1
        WF --> W2
        WF --> W3
        WF --> W4
    end

    subgraph Governance
        G1[Quality Gates]
        G2[Security Paths]
        G3[Review Triage]
        G4[Anti-Loop Protocol]
        
        GV --> G1
        GV --> G2
        GV --> G3
        GV --> G4
    end

    style Orchestration_Layer fill:#dfd,stroke:#333,stroke-width:2px
    style Triggers fill:#ffd,stroke:#333,stroke-width:1px
    style Workflows fill:#ffd,stroke:#333,stroke-width:1px
    style Governance fill:#ffd,stroke:#333,stroke-width:1px
```

---

## 3. Intelligence Layer

```mermaid
flowchart LR
    subgraph Intelligence_Layer
        direction LR
        
        RS[Routing Strategies] --> CB[Circuit Breakers]
        CB --> FC[Fallback Chains]
        FC --> AO[Agent Optimization]
        AO --> LI[Learning Integration]
        
        subgraph Routing_Strategies
            R1[Trigger-based]
            R2[Memory-augmented]
            R3[Local Model]
            R4[Learning-based]
            R5[Keyword Fallback]
            
            RS --> R1
            RS --> R2
            RS --> R3
            RS --> R4
            RS --> R5
        end
        
        subgraph Circuit_Breakers
            C1[Token Budget]
            C2[Step Limit]
            C3[Timeout]
            C4[Failure Limit]
            C5[Scope Creep]
            C6[Stuck Detection]
            
            CB --> C1
            CB --> C2
            CB --> C3
            CB --> C4
            CB --> C5
            CB --> C6
        end
        
        subgraph Fallback_Chains
            F1[Explore → Sisyphus-Junior → Atlas]
            F2[Librarian → Explore → Sisyphus-Junior]
            F3[Atlas → Sisyphus-Junior → Hephaestus]
            F4[Hephaestus → Oracle → Sisyphus]
            
            FC --> F1
            FC --> F2
            FC --> F3
            FC --> F4
        end
        
        subgraph Agent_Optimization
            A1[Complexity Scoring]
            A2[Scope Detection]
            A3[Result Store]
            A4[Review Triage]
            A5[Delegation Logger]
            
            AO --> A1
            AO --> A2
            AO --> A3
            AO --> A4
            AO --> A5
        end
        
        subgraph Learning_Integration
            L1[Q-Learning]
            L2[Outcome Logging]
            L3[Weight Updates]
            L4[Pattern Evolution]
            
            LI --> L1
            LI --> L2
            LI --> L3
            LI --> L4
        end
    end

    style Intelligence_Layer fill:#ddf,stroke:#333,stroke-width:2px
```

---

## 4. Memory Layer

```mermaid
flowchart TB
    subgraph Memory_Layer
        direction TB
        
        ST[Storage] --> RT[Retrieval]
        RT --> CP[Cognitive Processes]
        
        subgraph Storage
            direction LR
            VS[Vector Store] --- GS[Graph Store] --- RS[Relational Store]
            
            V1[Semantic Search]
            V2[Embedding Cache]
            V3[Index Management]
            
            G1[Knowledge Graph]
            G2[Entity Relations]
            G3[Path Finding]
            
            R1[SQLite Persistence]
            R2[Session State]
            R3[Outcome Logs]
            
            VS --> V1
            VS --> V2
            VS --> V3
            GS --> G1
            GS --> G2
            GS --> G3
            RS --> R1
            RS --> R2
            RS --> R3
        end
        
        subgraph Retrieval
            direction LR
            RTR[Semantic Search] --- RRM[Memory Search] --- RFR[Forgetting Recall]
            
            RT1[Unified Memory]
            RT2[Athena Context]
            RT3[Session Recall]
            RT4[TEMPR Search]
            
            RTR --> RT1
            RTR --> RT2
            RRM --> RT3
            RRM --> RT4
        end
        
        subgraph Cognitive_Processes
            direction LR
            
            CP1[Forgetting] --> CP2[Priority]
            CP2 --> CP3[Sleep]
            CP3 --> CP4[Retention]
            CP4 --> CP5[Reconsolidation]
            CP5 --> CP6[Trust]
            
            subgraph Forgetting
                F1[TTL Management]
                F2[Importance Decay]
                F3[Access Tracking]
            end
            
            subgraph Priority
                P1[Recency Score]
                P2[Access Frequency]
                P3[Relevance Weight]
            end
            
            subgraph Sleep
                S1[Consolidation]
                S2[Memory Transfer]
                S3[Schema Formation]
            end
            
            subgraph Retention
                R1[Importance Threshold]
                R2[Emotional Tagging]
                R3[Pattern Detection]
            end
            
            subgraph Reconsolidation
                RC1[Memory Update]
                RC2[Context Refresh]
                RC3[Association Rebuild]
            end
            
            subgraph Trust
                T1[Confidence Score]
                T2[Source Verification]
                T3[Consistency Check]
            end
            
            CP1 --> F1
            CP1 --> F2
            CP1 --> F3
            CP2 --> P1
            CP2 --> P2
            CP2 --> P3
            CP3 --> S1
            CP3 --> S2
            CP3 --> S3
            CP4 --> R1
            CP4 --> R2
            CP4 --> R3
            CP5 --> RC1
            CP5 --> RC2
            CP5 --> RC3
            CP6 --> T1
            CP6 --> T2
            CP6 --> T3
        end
    end

    style Memory_Layer fill:#fdd,stroke:#333,stroke-width:2px
    style Storage fill:#fee,stroke:#333,stroke-width:1px
    style Retrieval fill:#fee,stroke:#333,stroke-width:1px
    style Cognitive_Processes fill:#fee,stroke:#333,stroke-width:1px
```

---

## 5. Learning Engine

```mermaid
flowchart LR
    subgraph Learning_Engine
        direction LR
        
        QL[Q-Learning] --> MAB[Multi-Armed Bandits]
        MAB --> EWC[EWC]
        EWC --> MAML[MAML]
        MAML --> AR[Adaptive Routing]
        AR --> AB[A/B Testing]
        
        subgraph Q-Learning
            Q1[State Space]
            Q2[Action Space]
            Q3[Reward Signal]
            Q4[Policy Update]
            Q5[Exploration/Exploitation]
            
            QL --> Q1
            QL --> Q2
            QL --> Q3
            QL --> Q4
            QL --> Q5
        end
        
        subgraph Multi-Armed_Bandits
            M1[Thompson Sampling]
            M2[UCB1]
            M3[Epsilon-Greedy]
            M4[Contextual Bandits]
            
            MAB --> M1
            MAB --> M2
            MAB --> M3
            MAB --> M4
        end
        
        subgraph Elastic_Weight_Consolidation
            E1[Fisher Matrix]
            E2[Importance Weights]
            E3[Regularization]
            E4[Plasticity Control]
            
            EWC --> E1
            EWC --> E2
            EWC --> E3
            EWC --> E4
        end
        
        subgraph Model_Agnostic_Meta_Learning
            M1[Fast Adaptation]
            M2[Gradient Alignment]
            M3[Task Distribution]
            M4[Few-shot Learning]
            
            MAML --> M1
            MAML --> M2
            MAML --> M3
            MAML --> M4
        end
        
        subgraph Adaptive_Routing
            A1[Complexity Score]
            A2[Agent Selection]
            A3[Strategy Match]
            A4[Performance Track]
            
            AR --> A1
            AR --> A2
            AR --> A3
            AR --> A4
        end
        
        subgraph A/B_Testing
            A1[Variant Selection]
            A2[Statistical Testing]
            A3[Success Metrics]
            A4[Weight Evolution]
            
            AB --> A1
            AB --> A2
            AB --> A3
            AB --> A4
        end
    end

    style Learning_Engine fill:#dfd,stroke:#333,stroke-width:2px
```

---

## 6. Infrastructure Layer

```mermaid
flowchart TB
    subgraph Infrastructure_Layer
        direction TB
        
        PR[Proxy System] --> GS[GoldenSpine]
        GS --> MN[Monitoring]
        MN --> RS[Resilience]
        RS --> VP[VPN Rotation]
        
        subgraph Proxy_System
            P1[HTTP Proxy]
            P2[HTTPS Proxy]
            P3[SOCKS5 Proxy]
            P4[Load Balancing]
            P5[Health Checks]
            
            PR --> P1
            PR --> P2
            PR --> P3
            PR --> P4
            PR --> P5
        end
        
        subgraph GoldenSpine
            G1[Inference Engine]
            G2[Model Management]
            G3[Fallback Pipeline]
            G4[Health Monitoring]
            G5[Latency Tracking]
            
            GS --> G1
            GS --> G2
            GS --> G3
            GS --> G4
            GS --> G5
        end
        
        subgraph Monitoring
            M1[Metrics Collection]
            M2[Log Aggregation]
            M3[Alerting]
            M4[Dashboards]
            M5[Tracing]
            
            MN --> M1
            MN --> M2
            MN --> M3
            MN --> M4
            MN --> M5
        end
        
        subgraph Resilience
            R1[Retry Logic]
            R2[Circuit Breaker]
            R3[Rate Limiting]
            R4[Timeout Management]
            R5[Fallback Chains]
            
            RS --> R1
            RS --> R2
            RS --> R3
            RS --> R4
            RS --> R5
        end
        
        subgraph VPN_Rotation
            V1[IP Pool]
            V2[Health Checks]
            V3[Geo Targeting]
            V4[Protocol Support]
            V5[Failover]
            
            VP --> V1
            VP --> V2
            VP --> V3
            VP --> V4
            VP --> V5
        end
    end

    style Infrastructure_Layer fill:#dff,stroke:#333,stroke-width:2px
```

---

## 7. Local LLM Pipeline

```mermaid
sequenceDiagram
    participant User as User Input
    participant Emb as Embedding Model
    participant Ros as Rosetta
    participant Rea as Reasoner
    participant Tool as Tool Calling
    participant MCP as MCP Tools
    participant Out as Output

    User->>Emb: Raw Text
    Emb->>Ros: Embedding Vector
    
    Ros->>Rea: Contextualized Input
    Rea->>Tool: Reasoning Complete
    
    Tool->>MCP: Tool Selection
    MCP-->>Tool: Tool Result
    
    Tool->>Ros: Tool Context
    Ros->>Rea: Enhanced Context
    
    Rea->>Out: Final Response
    Out-->>User: Structured Output
    
    note over Emb, Out: Pipeline runs continuously until completion
    
    note right of Ros: Transforms embeddings<br/>into LLM-compatible<br/>token sequences
    
    note right of Tool: Determines when to<br/>call external tools<br/>vs generate response
    
    note right of MCP: File, Git, GitHub,<br/>Notion, Context7,<br/>Sequential Thinking
```

---

## 8. Data Flow

```mermaid
sequenceDiagram
    participant User as User Input
    participant Orch as Orchestration
    participant Int as Intelligence
    participant Mem as Memory
    participant LLM as Local LLM
    participant Act as Action
    participant Learn as Learning Engine
    participant DB as Data Layer

    User->>Orch: Request
    
    Orch->>Int: Route Task
    Int->>Mem: Query Context
    Mem-->>Int: Context Results
    
    Int->>LLM: Decision + Context
    LLM-->>Int: Inference Result
    
    Int->>Act: Execute Action
    
    Act->>DB: Log Action
    
    Act->>Learn: Record Outcome
    Learn->>Mem: Update Memory
    Learn->>Int: Update Routing
    
    Act-->>User: Response
    
    note over Orch, Learn: Continuous feedback loop
    
    note right of Orch: Agent Loop, Triggers,<br/>BMAD Workflows
    note right of Int: Circuit Breakers,<br/>Fallback Chains,<br/>Optimization
    note right of Mem: Vector/Graph/Relational<br/>Cognitive Processes
    note right of LLM: GoldenSpine, Rosetta,<br/>Tool Calling
    note right of Learn: Q-Learning, A/B Testing<br/>Adaptive Routing
```

---

## Architecture Summary

The N-Xyme MIND system is built on 7 interconnected layers:

1. **Orchestration Layer**: Manages agent loops, triggers, and workflow execution via BMAD integration
2. **Intelligence Layer**: Provides intelligent routing with circuit breakers, fallback chains, and learning integration
3. **Memory Core**: Stores and retrieves data across vector, graph, and relational stores with cognitive processes
4. **Learning Engine**: Continuously improves routing and agent selection through Q-learning and adaptive strategies
5. **Infrastructure**: Provides resilient infrastructure with proxy systems, GoldenSpine inference, and monitoring
6. **Local LLM Pipeline**: Processes user input through embedding, reasoning, and tool calling stages
7. **Data Layer**: Persists all system state including session history, outcomes, and learned patterns

The data flow forms a continuous feedback loop where user inputs traverse the entire system, with the learning engine continuously optimizing based on outcomes.