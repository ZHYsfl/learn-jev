这里我们假设你有ai agent基础，如果没有也没关系，可以直接看 chapter/chapter_2/agent_runtime 学习。

我们知道LLM Based驱动的Agent通过tool calling实现工具（动作）编排，但有些任务很简单，却需要一个一个自回归生成文本流，再解析出tool call执行，导致成本高，延迟也高。



