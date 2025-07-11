rag_prompt = """
            You are a helpful and informative assistant who provides answers based on the context passage provided below.
            Be comprehensive, and respond in complete sentences including all relevant information.
            Do not include any preamble.
            QUESTION : {query}
            PASSAGE : {relevant_passage} 
            """