from com.agent.model.contants.contant import COMPRESSION_MODEL, MAX_MESSAGES, COMPRESSED_MESSAGES_COUNT
from typing import List
from com.agent.model.workflow.llm.llm_factory import LLMFactory
from com.agent.model.workflow.prompt.compressionPrompt import COMPRESSION_PROMPT

class CompressionHandle:

    def compressMessages(self, messages: List[dict]) -> List[dict]:
        if len(messages) <= MAX_MESSAGES:
            return messages

        llm = LLMFactory.create_openai_llm()
        new_message = messages[-COMPRESSED_MESSAGES_COUNT:]

        if COMPRESSION_MODEL == 0:
            return new_message
        else :
            prompt = COMPRESSION_PROMPT.format(
                messages = messages[:len(messages)-COMPRESSED_MESSAGES_COUNT]
            )
            new_message.append(llm.invoke(prompt))
        
        return new_message