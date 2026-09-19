这里我们假设你有 强化学习 / ai agent 基础，如果没有也没关系，可以直接看 chapter/chapter_2/agent_runtime 学习LLM Based Agent的最小实现。

我们知道LLM Based驱动的Agent通过tool calling实现工具（动作）编排，但有些任务很简单，却需要一个一个自回归生成文本流，再解析出tool call执行，导致成本高，延迟也高。

jev model并不提高模型的智力上限，智力上限还是LLM的事情。但对于简单的自动化工作流，更好的方案可能是成本更低、延迟更低的Jev Based Agent而不是LLM Based Agent.

由jev model驱动的agent实现在：chapter/chapter_2/code/jev_based_agent.py