import ollama
from ollama import Client
import os
from typing import List, Dict
from django.conf import settings


class OllamaService:
    """Service to interact with Ollama API"""
    
    def __init__(self, base_url=None):
        self.base_url = base_url or getattr(settings, 'OLLAMA_BASE_URL', 'http://localhost:11434')
        self._setup_client()
    
    def _setup_client(self):
        """Setup Ollama client with proper URL"""
        # Normalize URL
        url = self.base_url.strip()
        if not url.startswith('http://') and not url.startswith('https://'):
            url = f'https://{url}'
        
        # Remove trailing slash
        url = url.rstrip('/')
        
        # Create client with explicit host
        try:
            self.client = Client(host=url)
        except Exception as e:
            print(f"Warning: Could not create Ollama client: {e}")
            # Fallback to default
            self.client = Client()
    
    def list_models(self) -> List[Dict]:
        """List all available models from Ollama"""
        try:
            response = self.client.list()
            
            # Handle different response formats
            if hasattr(response, 'models'):
                model_list = response.models
            elif isinstance(response, dict) and 'models' in response:
                model_list = response['models']
            elif isinstance(response, list):
                model_list = response
            else:
                model_list = []
            
            result = []
            for model in model_list:
                # Handle Model objects from ollama library
                if hasattr(model, 'model'):
                    model_name = model.model
                    model_info = {
                        'name': model_name,
                        'size': getattr(model, 'size', 0),
                        'modified_at': getattr(model, 'modified_at', ''),
                    }
                elif hasattr(model, 'name'):
                    model_name = model.name
                    model_info = {
                        'name': model_name,
                        'size': getattr(model, 'size', 0),
                        'modified_at': getattr(model, 'modified_at', ''),
                    }
                elif isinstance(model, dict):
                    # Handle dict format (from API responses)
                    model_name = model.get('model') or model.get('name', '')
                    model_info = {
                        'name': model_name,
                        'size': model.get('size', 0),
                        'modified_at': model.get('modified_at', ''),
                    }
                else:
                    continue
                
                if model_info['name']:
                    result.append(model_info)
            
            return result
        except Exception as e:
            # Don't print traceback for connection errors
            error_msg = str(e)
            if '10061' not in error_msg and 'connection' not in error_msg.lower():
                import traceback
                traceback.print_exc()
            return []
    
    def get_model_info(self, model_name: str) -> Dict:
        """Get information about a specific model"""
        try:
            model_info = self.client.show(model_name)
            
            if hasattr(model_info, 'modelfile'):
                return {
                    'name': model_name,
                    'modelfile': model_info.modelfile,
                    'parameters': getattr(model_info, 'parameters', ''),
                    'template': getattr(model_info, 'template', ''),
                }
            elif isinstance(model_info, dict):
                return {
                    'name': model_name,
                    'modelfile': model_info.get('modelfile', ''),
                    'parameters': model_info.get('parameters', ''),
                    'template': model_info.get('template', ''),
                }
            return {}
        except Exception as e:
            print(f"Error getting model info for {model_name}: {e}")
            return {}

