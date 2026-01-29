"""
Prompt augmenter for constructing augmented prompts with retrieved context.
"""

from .models import DocumentChunk, SearchResult


class PromptAugmenter:
    """
    Construct augmented prompts with retrieved context.

    This class formats context chunks with source attribution and creates
    prompts that instruct the agent to respond based only on provided context.
    """

    # RAG instructions that enforce context-only responses and prevent hallucination
    RAG_INSTRUCTIONS = """
IMPORTANT INSTRUCTIONS FOR RESPONDING:
1. You MUST respond ONLY based on the context provided below. Do not use any external knowledge.
2. You MUST cite the sources for your information using the source identifiers provided.
3. If the provided context does not contain enough information to answer the question, you MUST explicitly state "I don't have enough information in the provided sources to answer this question."
4. You MUST NOT fabricate, guess, or hallucinate any information that is not present in the context.
5. When answering, quote or paraphrase directly from the provided context rather than generating novel claims.
6. If you are uncertain about any part of your answer, acknowledge the uncertainty explicitly.
"""

    def augment_prompt(
        self, query: str, context_chunks: list[SearchResult] | list[DocumentChunk], system_prompt: str
    ) -> str:
        """
        Create an augmented prompt with context and instructions.

        Args:
            query: Original user query
            context_chunks: Retrieved context chunks (SearchResult or DocumentChunk objects)
            system_prompt: Agent's base system prompt

        Returns:
            Augmented prompt string ready for Ollama
        """
        # Handle empty context
        if not context_chunks:
            return self._create_no_context_prompt(query, system_prompt)

        # Extract DocumentChunk from SearchResult if needed
        chunks = []
        for item in context_chunks:
            if isinstance(item, SearchResult):
                chunks.append(item.chunk)
            elif isinstance(item, DocumentChunk):
                chunks.append(item)
            else:
                # Handle any other type by trying to access chunk attribute
                chunks.append(getattr(item, "chunk", item))

        # Build the augmented prompt
        prompt_parts = [
            system_prompt,
            "",
            self.RAG_INSTRUCTIONS,
            "",
            "CONTEXT INFORMATION:",
            "=" * 80,
        ]

        # Add formatted context chunks
        for i, chunk in enumerate(chunks, start=1):
            formatted_chunk = self.format_context_chunk(chunk, i)
            prompt_parts.append(formatted_chunk)
            prompt_parts.append("-" * 80)

        # Add the user query
        prompt_parts.extend(["", "USER QUERY:", query, "", "YOUR RESPONSE (remember to cite sources):"])

        return "\n".join(prompt_parts)

    def format_context_chunk(self, chunk: DocumentChunk, index: int) -> str:
        """
        Format a single context chunk with source attribution.

        Args:
            chunk: Document chunk to format
            index: Index of the chunk in the context list

        Returns:
            Formatted chunk string with source information
        """
        # Determine source label based on type
        if chunk.source_type == "web":
            source_label = f"Web Source: {chunk.source_identifier}"
        elif chunk.source_type == "database":
            source_label = f"Database Table: {chunk.source_identifier}"
        else:
            source_label = f"Source: {chunk.source_identifier}"

        # Format the chunk with clear attribution
        formatted = [f"[Context {index}]", f"Source Type: {chunk.source_type}", f"{source_label}", "", chunk.text]

        return "\n".join(formatted)

    def _create_no_context_prompt(self, query: str, system_prompt: str) -> str:
        """
        Create a prompt when no context is available.

        Args:
            query: Original user query
            system_prompt: Agent's base system prompt

        Returns:
            Prompt instructing the agent to state no information is available
        """
        prompt_parts = [
            system_prompt,
            "",
            "IMPORTANT: No relevant context was found in the knowledge sources for this query.",
            "You MUST respond by stating that you don't have information available to answer this question.",
            "Do NOT attempt to answer from general knowledge or make up information.",
            "",
            "USER QUERY:",
            query,
            "",
            "YOUR RESPONSE:",
        ]

        return "\n".join(prompt_parts)
