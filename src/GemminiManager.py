import google.generativeai as genai

class GeminiManager:    
    _instance = None
    _initialized = False
    
    def __new__(cls):
        if cls._instance is None:
            cls._instance = super(GeminiManager, cls).__new__(cls)
        return cls._instance
    
    def initialize(self, api_key):
        """Initialize Gemini AI with proper error handling"""
        try:
            if not api_key or not isinstance(api_key, str) or len(api_key.strip()) == 0:
                print("Notice: Gemini API key not provided - running in limited mode")
                self._initialized = False
                return False
            
            clean_key = api_key.strip().strip('"\'')
            genai.configure(api_key=clean_key)
            self._initialized = True
            return True
        except Exception as e:
            print(f"Error initializing Gemini AI: {str(e)}")
            self._initialized = False
            return False

    def is_initialized(self):
        """Check if Gemini AI is initialized with valid API key"""
        return self._initialized
    
    def get_valid_model_name(self, model_name):
        """Validate and return correct Gemini model name"""
        valid_models = {
            'gemini-1.5-flash': 'gemini-1.5-flash',
            'gemini-1.5-pro': 'gemini-1.5-pro',
            'gemini-2.0-flash': 'gemini-2.0-flash',
            'gemini-2.0-flash-lite': 'gemini-2.0-flash-lite'
        }
        return valid_models.get(model_name.strip().lower(), 'gemini-2.0-flash')

    @classmethod
    def get_instance(cls):
        """Get singleton instance"""
        if cls._instance is None:
            cls._instance = cls()
        return cls._instance