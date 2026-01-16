/**
 * Equities AI - Multi-Provider API Client
 * Supports multiple AI backends with latest 2026 models
 * Default: Gemini 3 Flash
 *
 * Documentation Sources:
 * - Gemini 3: https://ai.google.dev/gemini-api/docs/gemini-3
 * - OpenAI GPT-5.2: https://platform.openai.com/docs/models/gpt-5.2
 * - Anthropic Claude 4.5: https://docs.anthropic.com/en/docs/about-claude/models/overview
 * - Mistral: https://docs.mistral.ai/getting-started/models
 * - xAI Grok: https://docs.x.ai/docs/models
 */

// Available AI Providers and Models (January 2026)
const AI_PROVIDERS = {
    google: {
        name: 'Google AI',
        baseUrl: 'https://generativelanguage.googleapis.com/v1beta',
        models: {
            'gemini-3-flash': {
                id: 'gemini-3-flash',
                name: 'Gemini 3 Flash',
                contextWindow: 1000000,
                maxOutput: 65536,
                inputPrice: 0.50,  // per 1M tokens
                outputPrice: 3.00,
                features: ['text', 'vision', 'audio', 'video', 'thinking', 'tools', 'caching'],
                thinkingLevels: ['minimal', 'low', 'medium', 'high'],
                default: true
            },
            'gemini-3-pro': {
                id: 'gemini-3-pro',
                name: 'Gemini 3 Pro',
                contextWindow: 2000000,
                maxOutput: 65536,
                inputPrice: 1.25,
                outputPrice: 5.00,
                features: ['text', 'vision', 'audio', 'video', 'thinking', 'tools', 'caching'],
                thinkingLevels: ['minimal', 'low', 'medium', 'high']
            },
            'gemini-2.5-flash': {
                id: 'gemini-2.5-flash',
                name: 'Gemini 2.5 Flash',
                contextWindow: 1000000,
                maxOutput: 65536,
                inputPrice: 0.15,
                outputPrice: 0.60,
                features: ['text', 'vision', 'thinking', 'tools']
            }
        }
    },
    openai: {
        name: 'OpenAI',
        baseUrl: 'https://api.openai.com/v1',
        models: {
            'gpt-5.2': {
                id: 'gpt-5.2',
                name: 'GPT-5.2',
                contextWindow: 400000,
                maxOutput: 128000,
                inputPrice: 5.00,
                outputPrice: 15.00,
                features: ['text', 'vision', 'reasoning', 'tools'],
                reasoningEffort: ['none', 'low', 'medium', 'high', 'xhigh']
            },
            'gpt-5.2-codex': {
                id: 'gpt-5.2-codex',
                name: 'GPT-5.2 Codex',
                contextWindow: 400000,
                maxOutput: 128000,
                inputPrice: 5.00,
                outputPrice: 15.00,
                features: ['text', 'code', 'reasoning', 'tools', 'agentic']
            },
            'gpt-5.1': {
                id: 'gpt-5.1',
                name: 'GPT-5.1',
                contextWindow: 256000,
                maxOutput: 64000,
                inputPrice: 2.50,
                outputPrice: 10.00,
                features: ['text', 'vision', 'reasoning', 'tools']
            },
            'gpt-5': {
                id: 'gpt-5',
                name: 'GPT-5',
                contextWindow: 128000,
                maxOutput: 32000,
                inputPrice: 2.00,
                outputPrice: 8.00,
                features: ['text', 'vision', 'tools']
            },
            'o3-mini': {
                id: 'o3-mini',
                name: 'o3-mini',
                contextWindow: 200000,
                maxOutput: 100000,
                inputPrice: 1.10,
                outputPrice: 4.40,
                features: ['text', 'reasoning', 'tools']
            }
        }
    },
    anthropic: {
        name: 'Anthropic',
        baseUrl: 'https://api.anthropic.com/v1',
        models: {
            'claude-opus-4.5': {
                id: 'claude-opus-4-5-20251101',
                name: 'Claude Opus 4.5',
                contextWindow: 200000,
                maxOutput: 32000,
                inputPrice: 5.00,
                outputPrice: 25.00,
                features: ['text', 'vision', 'thinking', 'tools', 'computer-use'],
                thinkingModes: ['enabled', 'disabled']
            },
            'claude-sonnet-4.5': {
                id: 'claude-sonnet-4-5-20241022',
                name: 'Claude Sonnet 4.5',
                contextWindow: 1000000,  // with beta header
                maxOutput: 64000,
                inputPrice: 3.00,
                outputPrice: 15.00,
                features: ['text', 'vision', 'thinking', 'tools', 'computer-use', 'batch']
            },
            'claude-haiku-4.5': {
                id: 'claude-haiku-4-5-20241022',
                name: 'Claude Haiku 4.5',
                contextWindow: 200000,
                maxOutput: 8192,
                inputPrice: 1.00,
                outputPrice: 5.00,
                features: ['text', 'vision', 'tools']
            }
        }
    },
    mistral: {
        name: 'Mistral AI',
        baseUrl: 'https://api.mistral.ai/v1',
        models: {
            'mistral-large-latest': {
                id: 'mistral-large-latest',
                name: 'Mistral Large 3',
                contextWindow: 256000,
                maxOutput: 32000,
                inputPrice: 2.00,
                outputPrice: 6.00,
                features: ['text', 'vision', 'tools', 'code']
            },
            'codestral-latest': {
                id: 'codestral-latest',
                name: 'Codestral',
                contextWindow: 256000,
                maxOutput: 32000,
                inputPrice: 0.30,
                outputPrice: 0.90,
                features: ['code', 'fill-in-middle']
            },
            'mistral-small-latest': {
                id: 'mistral-small-latest',
                name: 'Mistral Small',
                contextWindow: 128000,
                maxOutput: 32000,
                inputPrice: 0.20,
                outputPrice: 0.60,
                features: ['text', 'tools']
            }
        }
    },
    xai: {
        name: 'xAI',
        baseUrl: 'https://api.x.ai/v1',
        models: {
            'grok-4': {
                id: 'grok-4',
                name: 'Grok 4',
                contextWindow: 2000000,
                maxOutput: 131072,
                inputPrice: 3.00,
                outputPrice: 15.00,
                features: ['text', 'vision', 'reasoning', 'tools', 'search']
            },
            'grok-4-1-fast-reasoning': {
                id: 'grok-4-1-fast-reasoning',
                name: 'Grok 4.1 Fast (Reasoning)',
                contextWindow: 2000000,
                maxOutput: 131072,
                inputPrice: 2.00,
                outputPrice: 10.00,
                features: ['text', 'reasoning', 'tools', 'agentic']
            },
            'grok-code-fast-1': {
                id: 'grok-code-fast-1',
                name: 'Grok Code Fast',
                contextWindow: 256000,
                maxOutput: 32000,
                inputPrice: 0.50,
                outputPrice: 2.50,
                features: ['code', 'reasoning', 'agentic']
            },
            'grok-3': {
                id: 'grok-3',
                name: 'Grok 3',
                contextWindow: 131072,
                maxOutput: 32000,
                inputPrice: 1.00,
                outputPrice: 5.00,
                features: ['text', 'vision', 'tools']
            }
        }
    },
    openrouter: {
        name: 'OpenRouter',
        baseUrl: 'https://openrouter.ai/api/v1',
        models: {
            // OpenRouter provides access to all models via unified API
            'auto': {
                id: 'auto',
                name: 'Auto (Best Match)',
                contextWindow: 128000,
                maxOutput: 32000,
                inputPrice: 'varies',
                outputPrice: 'varies',
                features: ['text', 'routing']
            }
        }
    }
};

// Default configuration
const DEFAULT_CONFIG = {
    provider: 'google',
    model: 'gemini-3-flash',
    thinkingLevel: 'medium',
    temperature: 0.7,
    maxTokens: 8192,
    timeout: 120000
};

/**
 * Multi-Provider AI Client
 */
class AIClient {
    constructor(config = {}) {
        this.config = { ...DEFAULT_CONFIG, ...config };
        this.apiKeys = this.loadApiKeys();
        this.currentProvider = AI_PROVIDERS[this.config.provider];
        this.currentModel = this.currentProvider?.models[this.config.model];
    }

    // Load API keys from localStorage or config
    loadApiKeys() {
        const keys = {};
        try {
            const stored = localStorage.getItem('ai_api_keys');
            if (stored) {
                Object.assign(keys, JSON.parse(stored));
            }
        } catch (e) {
            console.warn('Could not load API keys from localStorage');
        }
        return keys;
    }

    // Save API keys
    saveApiKeys(keys) {
        this.apiKeys = { ...this.apiKeys, ...keys };
        try {
            localStorage.setItem('ai_api_keys', JSON.stringify(this.apiKeys));
        } catch (e) {
            console.warn('Could not save API keys to localStorage');
        }
    }

    // Set API key for a provider
    setApiKey(provider, key) {
        this.saveApiKeys({ [provider]: key });
    }

    // Get current provider info
    getProviderInfo() {
        return {
            provider: this.config.provider,
            providerName: this.currentProvider?.name,
            model: this.config.model,
            modelName: this.currentModel?.name,
            features: this.currentModel?.features || [],
            contextWindow: this.currentModel?.contextWindow,
            pricing: {
                input: this.currentModel?.inputPrice,
                output: this.currentModel?.outputPrice
            }
        };
    }

    // List all available providers and models
    static listProviders() {
        return Object.entries(AI_PROVIDERS).map(([id, provider]) => ({
            id,
            name: provider.name,
            models: Object.entries(provider.models).map(([modelId, model]) => ({
                id: modelId,
                name: model.name,
                contextWindow: model.contextWindow,
                features: model.features,
                default: model.default || false
            }))
        }));
    }

    // Switch provider and model
    switchProvider(provider, model = null) {
        if (!AI_PROVIDERS[provider]) {
            throw new Error(`Unknown provider: ${provider}`);
        }

        this.config.provider = provider;
        this.currentProvider = AI_PROVIDERS[provider];

        if (model) {
            if (!this.currentProvider.models[model]) {
                throw new Error(`Unknown model: ${model} for provider ${provider}`);
            }
            this.config.model = model;
        } else {
            // Select default model for provider
            const defaultModel = Object.entries(this.currentProvider.models)
                .find(([_, m]) => m.default)?.[0] || Object.keys(this.currentProvider.models)[0];
            this.config.model = defaultModel;
        }

        this.currentModel = this.currentProvider.models[this.config.model];
        return this.getProviderInfo();
    }

    // Build request headers based on provider
    buildHeaders(provider) {
        const headers = {
            'Content-Type': 'application/json'
        };

        const apiKey = this.apiKeys[provider];
        if (!apiKey) {
            console.warn(`No API key set for provider: ${provider}`);
        }

        switch (provider) {
            case 'google':
                // Google uses query param for API key
                break;
            case 'openai':
            case 'openrouter':
                headers['Authorization'] = `Bearer ${apiKey}`;
                break;
            case 'anthropic':
                headers['x-api-key'] = apiKey;
                headers['anthropic-version'] = '2024-10-22';
                headers['anthropic-beta'] = 'context-1m-2025-08-07';
                break;
            case 'mistral':
                headers['Authorization'] = `Bearer ${apiKey}`;
                break;
            case 'xai':
                headers['Authorization'] = `Bearer ${apiKey}`;
                break;
        }

        return headers;
    }

    // Build request body based on provider
    buildRequestBody(messages, options = {}) {
        const provider = this.config.provider;
        const model = this.currentModel;
        const mergedOptions = { ...this.config, ...options };

        switch (provider) {
            case 'google':
                return this.buildGoogleRequest(messages, model, mergedOptions);
            case 'openai':
            case 'openrouter':
                return this.buildOpenAIRequest(messages, model, mergedOptions);
            case 'anthropic':
                return this.buildAnthropicRequest(messages, model, mergedOptions);
            case 'mistral':
                return this.buildMistralRequest(messages, model, mergedOptions);
            case 'xai':
                return this.buildXAIRequest(messages, model, mergedOptions);
            default:
                throw new Error(`Unknown provider: ${provider}`);
        }
    }

    // Google Gemini request format
    buildGoogleRequest(messages, model, options) {
        const contents = messages.map(msg => ({
            role: msg.role === 'assistant' ? 'model' : 'user',
            parts: [{ text: msg.content }]
        }));

        const body = {
            contents,
            generationConfig: {
                temperature: options.temperature,
                maxOutputTokens: options.maxTokens,
                topP: options.topP || 0.95
            }
        };

        // Gemini 3 thinking levels
        if (model.thinkingLevels && options.thinkingLevel) {
            body.generationConfig.thinkingConfig = {
                thinkingLevel: options.thinkingLevel.toUpperCase()
            };
        }

        // Tool/function calling
        if (options.tools) {
            body.tools = [{
                functionDeclarations: options.tools
            }];
        }

        return body;
    }

    // OpenAI/OpenRouter request format
    buildOpenAIRequest(messages, model, options) {
        const body = {
            model: model.id,
            messages: messages.map(msg => ({
                role: msg.role,
                content: msg.content
            })),
            temperature: options.temperature,
            max_tokens: options.maxTokens
        };

        // GPT-5.2 reasoning effort
        if (model.reasoningEffort && options.reasoningEffort) {
            body.reasoning = {
                effort: options.reasoningEffort
            };
        }

        // Tool calling
        if (options.tools) {
            body.tools = options.tools.map(tool => ({
                type: 'function',
                function: tool
            }));
        }

        return body;
    }

    // Anthropic Claude request format
    buildAnthropicRequest(messages, model, options) {
        // Convert messages to Anthropic format
        const systemMessage = messages.find(m => m.role === 'system');
        const chatMessages = messages.filter(m => m.role !== 'system');

        const body = {
            model: model.id,
            max_tokens: options.maxTokens,
            messages: chatMessages.map(msg => ({
                role: msg.role,
                content: msg.content
            }))
        };

        if (systemMessage) {
            body.system = systemMessage.content;
        }

        // Extended thinking for Claude 4.5
        if (model.thinkingModes && options.thinking) {
            body.thinking = {
                type: 'enabled',
                budget_tokens: options.thinkingBudget || 10000
            };
        }

        // Tool use
        if (options.tools) {
            body.tools = options.tools.map(tool => ({
                name: tool.name,
                description: tool.description,
                input_schema: tool.parameters
            }));
        }

        return body;
    }

    // Mistral request format
    buildMistralRequest(messages, model, options) {
        return {
            model: model.id,
            messages: messages.map(msg => ({
                role: msg.role,
                content: msg.content
            })),
            temperature: options.temperature,
            max_tokens: options.maxTokens,
            top_p: options.topP || 0.95
        };
    }

    // xAI Grok request format
    buildXAIRequest(messages, model, options) {
        const body = {
            model: model.id,
            messages: messages.map(msg => ({
                role: msg.role,
                content: msg.content
            })),
            temperature: options.temperature,
            max_tokens: options.maxTokens
        };

        // Grok search tool
        if (options.enableSearch && model.features.includes('search')) {
            body.tools = [{
                type: 'live_search'
            }];
        }

        return body;
    }

    // Get API endpoint URL
    getEndpoint() {
        const provider = this.config.provider;
        const baseUrl = this.currentProvider.baseUrl;
        const apiKey = this.apiKeys[provider];

        switch (provider) {
            case 'google':
                return `${baseUrl}/models/${this.currentModel.id}:generateContent?key=${apiKey}`;
            case 'openai':
            case 'openrouter':
            case 'mistral':
            case 'xai':
                return `${baseUrl}/chat/completions`;
            case 'anthropic':
                return `${baseUrl}/messages`;
            default:
                throw new Error(`Unknown provider: ${provider}`);
        }
    }

    // Parse response based on provider
    parseResponse(provider, response) {
        switch (provider) {
            case 'google':
                return {
                    content: response.candidates?.[0]?.content?.parts?.[0]?.text || '',
                    thinking: response.candidates?.[0]?.content?.parts?.find(p => p.thought)?.thought,
                    usage: {
                        inputTokens: response.usageMetadata?.promptTokenCount,
                        outputTokens: response.usageMetadata?.candidatesTokenCount,
                        thinkingTokens: response.usageMetadata?.thoughtsTokenCount
                    },
                    finishReason: response.candidates?.[0]?.finishReason
                };

            case 'openai':
            case 'openrouter':
                return {
                    content: response.choices?.[0]?.message?.content || '',
                    reasoning: response.choices?.[0]?.message?.reasoning,
                    usage: {
                        inputTokens: response.usage?.prompt_tokens,
                        outputTokens: response.usage?.completion_tokens,
                        reasoningTokens: response.usage?.completion_tokens_details?.reasoning_tokens
                    },
                    finishReason: response.choices?.[0]?.finish_reason
                };

            case 'anthropic':
                const textBlock = response.content?.find(b => b.type === 'text');
                const thinkingBlock = response.content?.find(b => b.type === 'thinking');
                return {
                    content: textBlock?.text || '',
                    thinking: thinkingBlock?.thinking,
                    usage: {
                        inputTokens: response.usage?.input_tokens,
                        outputTokens: response.usage?.output_tokens
                    },
                    finishReason: response.stop_reason
                };

            case 'mistral':
                return {
                    content: response.choices?.[0]?.message?.content || '',
                    usage: {
                        inputTokens: response.usage?.prompt_tokens,
                        outputTokens: response.usage?.completion_tokens
                    },
                    finishReason: response.choices?.[0]?.finish_reason
                };

            case 'xai':
                return {
                    content: response.choices?.[0]?.message?.content || '',
                    usage: {
                        inputTokens: response.usage?.prompt_tokens,
                        outputTokens: response.usage?.completion_tokens
                    },
                    finishReason: response.choices?.[0]?.finish_reason
                };

            default:
                return { content: '', usage: {} };
        }
    }

    // Main chat completion method
    async chat(messages, options = {}) {
        const endpoint = this.getEndpoint();
        const headers = this.buildHeaders(this.config.provider);
        const body = this.buildRequestBody(messages, options);

        try {
            const response = await fetch(endpoint, {
                method: 'POST',
                headers,
                body: JSON.stringify(body),
                signal: AbortSignal.timeout(options.timeout || this.config.timeout)
            });

            if (!response.ok) {
                const error = await response.json().catch(() => ({}));
                throw new Error(error.error?.message || `API request failed: ${response.status}`);
            }

            const data = await response.json();
            return this.parseResponse(this.config.provider, data);

        } catch (error) {
            console.error('AI API Error:', error);
            throw error;
        }
    }

    // Stream chat completion (where supported)
    async *chatStream(messages, options = {}) {
        const endpoint = this.getEndpoint();
        const headers = this.buildHeaders(this.config.provider);
        const body = this.buildRequestBody(messages, { ...options, stream: true });

        // Add stream parameter
        if (this.config.provider !== 'google') {
            body.stream = true;
        }

        const response = await fetch(endpoint, {
            method: 'POST',
            headers,
            body: JSON.stringify(body)
        });

        if (!response.ok) {
            const error = await response.json().catch(() => ({}));
            throw new Error(error.error?.message || `API request failed: ${response.status}`);
        }

        const reader = response.body.getReader();
        const decoder = new TextDecoder();

        while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            const chunk = decoder.decode(value);
            const lines = chunk.split('\n').filter(line => line.startsWith('data: '));

            for (const line of lines) {
                const data = line.slice(6);
                if (data === '[DONE]') return;

                try {
                    const parsed = JSON.parse(data);
                    yield this.parseStreamChunk(parsed);
                } catch (e) {
                    // Skip unparseable chunks
                }
            }
        }
    }

    // Parse streaming chunk
    parseStreamChunk(chunk) {
        switch (this.config.provider) {
            case 'openai':
            case 'openrouter':
            case 'mistral':
            case 'xai':
                return {
                    content: chunk.choices?.[0]?.delta?.content || '',
                    finishReason: chunk.choices?.[0]?.finish_reason
                };
            case 'anthropic':
                if (chunk.type === 'content_block_delta') {
                    return { content: chunk.delta?.text || '' };
                }
                return { content: '' };
            default:
                return { content: '' };
        }
    }
}


/**
 * Equities AI Backend API Client
 * Handles communication with the FastAPI backend
 */
class EquitiesAPI {
    constructor(baseUrl = 'http://localhost:8000') {
        this.baseUrl = baseUrl;
        this.token = localStorage.getItem('auth_token');
        this.refreshToken = localStorage.getItem('refresh_token');

        // Initialize AI client with default Gemini 3 Flash
        this.ai = new AIClient({
            provider: 'google',
            model: 'gemini-3-flash',
            thinkingLevel: 'medium'
        });
    }

    // Configure AI provider
    configureAI(provider, model, apiKey) {
        if (apiKey) {
            this.ai.setApiKey(provider, apiKey);
        }
        return this.ai.switchProvider(provider, model);
    }

    // Get AI configuration
    getAIConfig() {
        return this.ai.getProviderInfo();
    }

    // List available AI providers
    getAvailableProviders() {
        return AIClient.listProviders();
    }

    // Helper method for making authenticated requests
    async request(endpoint, options = {}) {
        const url = `${this.baseUrl}${endpoint}`;
        const headers = {
            'Content-Type': 'application/json',
            ...options.headers
        };

        if (this.token) {
            headers['Authorization'] = `Bearer ${this.token}`;
        }

        try {
            const response = await fetch(url, {
                ...options,
                headers
            });

            if (response.status === 401) {
                const refreshed = await this.refreshAuthToken();
                if (refreshed) {
                    headers['Authorization'] = `Bearer ${this.token}`;
                    return fetch(url, { ...options, headers });
                }
            }

            return response;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    // Authentication
    async login(email, password) {
        const response = await this.request('/api/auth/login', {
            method: 'POST',
            body: JSON.stringify({ email, password })
        });

        if (response.ok) {
            const data = await response.json();
            this.token = data.access_token;
            this.refreshToken = data.refresh_token;
            localStorage.setItem('auth_token', this.token);
            localStorage.setItem('refresh_token', this.refreshToken);
            return data;
        }
        throw new Error('Login failed');
    }

    async logout() {
        await this.request('/api/auth/logout', { method: 'POST' });
        this.token = null;
        this.refreshToken = null;
        localStorage.removeItem('auth_token');
        localStorage.removeItem('refresh_token');
    }

    async refreshAuthToken() {
        if (!this.refreshToken) return false;

        try {
            const response = await fetch(`${this.baseUrl}/api/auth/refresh`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({ refresh_token: this.refreshToken })
            });

            if (response.ok) {
                const data = await response.json();
                this.token = data.access_token;
                localStorage.setItem('auth_token', this.token);
                return true;
            }
        } catch (error) {
            console.error('Token refresh failed:', error);
        }
        return false;
    }

    async getCurrentUser() {
        const response = await this.request('/api/auth/me');
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    // Analysis endpoints
    async triggerAnalysis(agentIds = null) {
        const body = agentIds ? { agent_ids: agentIds } : {};
        const response = await this.request('/api/analyze', {
            method: 'POST',
            body: JSON.stringify(body)
        });
        return response.json();
    }

    async getLatestAgentOutput(agentId) {
        const response = await this.request(`/api/agents/${agentId}/latest`);
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async getAgentHistory(agentId, page = 1, limit = 20) {
        const response = await this.request(
            `/api/agents/${agentId}/history?page=${page}&limit=${limit}`
        );
        if (response.ok) {
            return response.json();
        }
        return { items: [], total: 0 };
    }

    async runAgent(agentId) {
        const response = await this.request(`/api/agents/${agentId}/run`);
        return response.json();
    }

    async getLatestInsight() {
        const response = await this.request('/api/insights/latest');
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async getAgentPerformance(agentId) {
        const response = await this.request(`/api/performance/${agentId}`);
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async getAllAgentsStatus() {
        const agents = [
            'macro', 'geopolitical', 'commodities', 'sentiment',
            'fundamentals', 'technical', 'alternative', 'cross_asset',
            'event', 'risk', 'aggregation', 'learning'
        ];

        const results = {};
        await Promise.all(
            agents.map(async (agentId) => {
                const data = await this.getLatestAgentOutput(agentId);
                results[agentId] = data;
            })
        );
        return results;
    }

    // Settings endpoints
    async getSettings(category = null) {
        const endpoint = category
            ? `/api/settings/${category}`
            : '/api/settings';
        const response = await this.request(endpoint);
        if (response.ok) {
            return response.json();
        }
        return {};
    }

    async getSetting(category, key) {
        const response = await this.request(`/api/settings/${category}/${key}`);
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async updateSetting(category, key, value) {
        const response = await this.request(`/api/settings/${category}/${key}`, {
            method: 'PUT',
            body: JSON.stringify({ value })
        });
        return response.json();
    }

    async resetSettings() {
        const response = await this.request('/api/settings/reset?confirm=true', {
            method: 'POST'
        });
        return response.json();
    }

    async exportSettings() {
        const response = await this.request('/api/settings/export');
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async importSettings(settings) {
        const response = await this.request('/api/settings/import', {
            method: 'POST',
            body: JSON.stringify(settings)
        });
        return response.json();
    }

    async getSettingCategories() {
        const response = await this.request('/api/settings/categories');
        if (response.ok) {
            return response.json();
        }
        return [];
    }

    // Portfolio endpoints
    async getPortfolio() {
        const response = await this.request('/api/portfolio');
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async getPositions() {
        const response = await this.request('/api/portfolio/positions');
        if (response.ok) {
            return response.json();
        }
        return [];
    }

    async addPosition(position) {
        const response = await this.request('/api/portfolio/positions', {
            method: 'POST',
            body: JSON.stringify(position)
        });
        return response.json();
    }

    async updatePosition(positionId, updates) {
        const response = await this.request(`/api/portfolio/positions/${positionId}`, {
            method: 'PUT',
            body: JSON.stringify(updates)
        });
        return response.json();
    }

    async removePosition(positionId) {
        const response = await this.request(`/api/portfolio/positions/${positionId}`, {
            method: 'DELETE'
        });
        return response.ok;
    }

    // Trade signals and execution
    async getTradeSignals(status = null) {
        const endpoint = status
            ? `/api/signals?status=${status}`
            : '/api/signals';
        const response = await this.request(endpoint);
        if (response.ok) {
            return response.json();
        }
        return [];
    }

    async getExecutionOrders(status = null) {
        const endpoint = status
            ? `/api/execution/orders?status=${status}`
            : '/api/execution/orders';
        const response = await this.request(endpoint);
        if (response.ok) {
            return response.json();
        }
        return [];
    }

    async approveOrder(orderId) {
        const response = await this.request(`/api/execution/orders/${orderId}/approve`, {
            method: 'POST'
        });
        return response.json();
    }

    async rejectOrder(orderId, reason) {
        const response = await this.request(`/api/execution/orders/${orderId}/reject`, {
            method: 'POST',
            body: JSON.stringify({ reason })
        });
        return response.json();
    }

    // Market data
    async getMarketData(symbol) {
        const response = await this.request(`/api/market/${symbol}`);
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async getMarketRegime() {
        const response = await this.request('/api/market/regime');
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async getEventCalendar(startDate = null, endDate = null) {
        let endpoint = '/api/events';
        const params = [];
        if (startDate) params.push(`start=${startDate}`);
        if (endDate) params.push(`end=${endDate}`);
        if (params.length) endpoint += '?' + params.join('&');

        const response = await this.request(endpoint);
        if (response.ok) {
            return response.json();
        }
        return [];
    }

    // Performance and learning
    async getPerformanceMetrics(period = '30d') {
        const response = await this.request(`/api/performance?period=${period}`);
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async getAgentWeights() {
        const response = await this.request('/api/weights');
        if (response.ok) {
            return response.json();
        }
        return {};
    }

    async updateAgentWeight(agentId, weight) {
        const response = await this.request(`/api/weights/${agentId}`, {
            method: 'PUT',
            body: JSON.stringify({ weight })
        });
        return response.json();
    }

    async getCalibrationMetrics() {
        const response = await this.request('/api/calibration');
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    // Risk metrics
    async getRiskMetrics() {
        const response = await this.request('/api/risk/metrics');
        if (response.ok) {
            return response.json();
        }
        return null;
    }

    async getRiskAlerts() {
        const response = await this.request('/api/risk/alerts');
        if (response.ok) {
            return response.json();
        }
        return [];
    }

    // Health check
    async healthCheck() {
        try {
            const response = await fetch(`${this.baseUrl}/health`);
            return response.ok;
        } catch {
            return false;
        }
    }

    // Direct AI chat (uses configured AI provider)
    async aiChat(messages, options = {}) {
        return this.ai.chat(messages, options);
    }

    // Streaming AI chat
    aiChatStream(messages, options = {}) {
        return this.ai.chatStream(messages, options);
    }
}

// Create global API instance with Gemini 3 Flash as default
const api = new EquitiesAPI();

// Export for module usage
if (typeof module !== 'undefined' && module.exports) {
    module.exports = { AIClient, EquitiesAPI, AI_PROVIDERS, api };
}
