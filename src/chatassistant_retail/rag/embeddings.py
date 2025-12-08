"""Embeddings client for Azure OpenAI."""

import logging

from openai import AsyncAzureOpenAI

from chatassistant_retail.config import get_settings

logger = logging.getLogger(__name__)


class EmbeddingsClient:
    """Client for generating embeddings using Azure OpenAI."""

    def __init__(self, settings=None):
        """
        Initialize embeddings client.

        Args:
            settings: Optional Settings instance. If None, uses get_settings().
        """
        self.settings = settings or get_settings()
        self.client = AsyncAzureOpenAI(
            api_key=self.settings.azure_openai_api_key,
            api_version=self.settings.azure_openai_api_version,
            azure_endpoint=self.settings.azure_openai_endpoint,
        )
        self.cache = {} if self.settings.cache_embeddings else None
        logger.info("Initialized embeddings client")

    async def generate_embedding(self, text: str) -> list[float]:
        """
        Generate embedding vector for text.

        Args:
            text: Text to embed

        Returns:
            Embedding vector as list of floats
        """
        # Check cache first
        if self.cache is not None and text in self.cache:
            logger.debug(f"Cache hit for embedding: {text[:50]}...")
            return self.cache[text]

        try:
            response = await self.client.embeddings.create(
                model=self.settings.azure_openai_embedding_deployment,
                input=text,
            )

            embedding = response.data[0].embedding

            # Cache the result
            if self.cache is not None:
                self.cache[text] = embedding

            logger.debug(f"Generated embedding for: {text[:50]}... (dim: {len(embedding)})")
            return embedding

        except Exception as e:
            logger.error(f"Error generating embedding: {e}")
            raise

    async def generate_embeddings_batch(self, texts: list[str]) -> list[list[float]]:
        """
        Generate embeddings for multiple texts in batch.

        Args:
            texts: List of texts to embed

        Returns:
            List of embedding vectors
        """
        # Check which texts are already cached
        uncached_texts = []
        cached_embeddings = {}

        if self.cache is not None:
            for text in texts:
                if text in self.cache:
                    cached_embeddings[text] = self.cache[text]
                else:
                    uncached_texts.append(text)
        else:
            uncached_texts = texts

        # Generate embeddings for uncached texts
        new_embeddings = {}
        if uncached_texts:
            try:
                response = await self.client.embeddings.create(
                    model=self.settings.azure_openai_embedding_deployment,
                    input=uncached_texts,
                )

                for text, data in zip(uncached_texts, response.data):
                    embedding = data.embedding
                    new_embeddings[text] = embedding

                    # Cache the result
                    if self.cache is not None:
                        self.cache[text] = embedding

                logger.info(f"Generated {len(uncached_texts)} new embeddings")

            except Exception as e:
                logger.error(f"Error generating batch embeddings: {e}")
                raise

        # Combine cached and new embeddings in original order
        all_embeddings = {**cached_embeddings, **new_embeddings}
        return [all_embeddings[text] for text in texts]

    def clear_cache(self):
        """Clear the embeddings cache."""
        if self.cache is not None:
            self.cache.clear()
            logger.info("Embeddings cache cleared")

    def get_cache_size(self) -> int:
        """Get the number of cached embeddings."""
        return len(self.cache) if self.cache is not None else 0
