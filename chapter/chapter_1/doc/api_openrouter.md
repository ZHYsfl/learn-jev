# api_openrouter

我们可以从openrouter官方 https://openrouter.ai/~typesafe/jev-latest 使用jev-latest模型。它是一个"决策"模型：给定一段输入（state）和一组结构化问题（questions），按每个问题定义的评分标准返回判断结果。

```json
curl https://openrouter.ai/api/alpha/decisions \
  -H "Content-Type: application/json" \
  -H "Authorization: Bearer $OPENROUTER_API_KEY" \
  -d '{
    "model": "~typesafe/jev-latest",
    "state": "Help! My payouts have been failing for 3 days.",
    "questions": {
      "is_urgent": {
        "type": "noul",
        "instructions": "Does this message convey urgency?",
        "criteria": {
          "true": "Explicitly time-sensitive",
          "false": "No urgency expressed"
        }
      },
      "department": {
        "type": "choice",
        "instructions": "Which team should handle this?",
        "criteria": {
          "billing": "Payments, invoicing, refunds",
          "technical": "Bugs, outages, integrations",
          "sales": "Pricing, upgrades, new accounts"
        }
      },
      "frustration": {
        "type": "score",
        "instructions": "How frustrated is the customer?",
        "criteria": ["Calm", "Frustrated", "Very angry"]
      }
    }
  }
```

## 一、curl 命令部分                                                 
                                         
```bash                                                           
curl https://openrouter.ai/api/alpha/decisions \                
    -H "Content-Type: application/json" \            # 声明请求体格式是 JSON                                                         
    -H "Authorization: Bearer $OPENROUTER_API_KEY" \ # 认证：从环境变量读取 API key                                                
    -d '{...}'                                       # 请求体（POST的数据）                                                          
```

## 二、JSON 请求体字段

### 2.1 model                                                          
                                                    
```json                                                           
"model": "~typesafe/jev-latest"                                 
```

指定用哪个模型。                                                              
                                                                     
### 2.2 state                     
                                                                     
```json                                                           
"state": "Help! My payouts have been failing for 3 days."       
```                                                               
                                                                     
要被评估的原始输入，这里是用户的一句客服求助消息。模型将基于这段文本回答下面所有问题。

### 2.3 questions                                                      
                                                                     
最核心字段。一个对象：key 是你自定义的问题名，value 描述这道题怎么判。每个问题有三个子字段：                                        
                                                                    
┌──────────────┬─────────────────────────────────────────┐        
│ 子字段       │ 作用                                     │        
├──────────────┼─────────────────────────────────────────┤        
│ type         │ 答案的结构类型（bool / choice / score）  │        
├──────────────┼─────────────────────────────────────────┤        
│ instructions │ 自然语言指令：告诉模型"要判断什么"         │        
├──────────────┼─────────────────────────────────────────┤        
│ criteria     │ 评分标准：定义可选答案及每个答案的含义     │        
└──────────────┴─────────────────────────────────────────┘        
                                                                     
示例里用三个问题演示了三种 type：                                 
                               
① is_urgent — 二选一（bool）                                      
                                                                  
```json                                                           
  "type": "noul",   // 'noul'（Bernoulli 的简写）对应 if 语句 
  "instructions": "Does this message convey urgency?",        
  "criteria": {                                                   
    "true":  "Explicitly time-sensitive",                         
    "false": "No urgency expressed"                               
  }                                                               
```                                                               
                                       
criteria 是字典：key（true/false）是模型会返回的值，value 是判定标准（什么情况算 true，什么情况算 false）。模型判断这条消息是否表达紧急。

② department — 多选一（choice）

```json
"type": "choice",
"instructions": "Which team should handle this?",                         
"criteria": {                                                   
  "billing":   "Payments, invoicing, refunds",                  
  "technical": "Bugs, outages, integrations",                   
  "sales":     "Pricing, upgrades, new accounts"                
}                                                               
```                                                               
                                                                  
criteria 是选项表：模型必须从给定的 key（billing / technical / sales）中选且只选一个，每个选项配一段说明帮助模型理解边界。这里就是工单自动路由到哪个团队。

③ frustration — 程度打分（score）                                 

```json                                                           
  "type": "score",              
  "instructions": "How frustrated is the customer?",                                  
  "criteria": ["Calm", "Frustrated", "Very angry"]                
```                                                               
                                                                  
criteria 是数组，表示从低到高的刻度。模型返回一个等级（通常是对应下标，0/1/2），用来量化客户愤怒程度。                             
                                                                  
## 三、JSON 响应体字段                                                      
                                                                        
对照本例，模型预期会返回类似：                                    
                                               
```json                                                           
{                                                               
  "model": "typesafe/jev-1.13-20260917",   
  "answers": {                                                  
    "is_urgent": {                                              
      "type": "noul",                                           
      "noul": 0.95                    // ← 不是 true/false，而是概率 p                                                            
    },                                                          
    "department": {                                             
      "type": "choice",                                         
      "choice": "billing",           // ← argmax 后的最终选择   
      "probabilities": { "technical": 0.13, "sales": 0, "billing": 0.87 },                                                
      "confidence": 0.81                                        
    },                                                          
    "frustration": {                                            
      "type": "score",                                          
      "score": 1.04,                 // ← 连续值，落在 0~2 刻度上                                                                
      "legend": { "0": "Calm", "1": "Frustrated", "2": "Very angry" },                                                         
      "probabilities": { "0": 0, "1": 0.96, "2": 0.04 },        
      "confidence": 0.93                                        
    }                                                           
  },                                                            
  "usage": { "input_tokens": 427, "output_tokens": 73, "cost": 0.000017934 },                                                    
  "id": "gen-dec-1789833910-ssMftLvv1s4gz8pkHvvF",       
  "provider": "TypeSafe"                                        
}                                                               
```
