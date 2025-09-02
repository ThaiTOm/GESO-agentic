from typing import Dict, Any, Optional

class BasePrompt:
    """
    Base class for all prompts in the system.
    
    This class provides a foundation for creating and managing prompts for language models.
    It handles template storage and variable substitution.
    """
    
    def __init__(self, template: str, name: Optional[str] = None):
        """
        Initialize a new BasePrompt.
        
        Args:
            template (str): The prompt template string with placeholders for variables.
            name (Optional[str]): A name for the prompt, useful for identification.
        """
        self.template = template
        self.name = name or self.__class__.__name__
    
    def format(self, **kwargs: Any) -> str:
        """
        Format the prompt template with the provided variables.
        
        Args:
            **kwargs: Variable key-value pairs to substitute in the template.
            
        Returns:
            str: The formatted prompt string.
        """
        try:
            return self.template.format(**kwargs)
        except KeyError as e:
            raise KeyError(f"Missing required variable in prompt template: {e}")
    
    def __str__(self) -> str:
        """
        Return the template string.
        
        Returns:
            str: The prompt template string.
        """
        return self.template
    
    def __repr__(self) -> str:
        """
        Return a string representation of the prompt.
        
        Returns:
            str: A string representation including the class name and prompt name.
        """
        return f"{self.__class__.__name__}(name='{self.name}')"