// API Configuration
const API_BASE_URL = 'http://127.0.0.1:5000/api';
let authToken = localStorage.getItem('authToken');

// API Helper Functions
class API {
    static async request(endpoint, options = {}) {
        const url = `${API_BASE_URL}${endpoint}`;
        const config = {
            headers: {
                'Content-Type': 'application/json',
                ...options.headers
            },
            ...options
        };

        // Add auth token if available
        if (authToken) {
            config.headers['Authorization'] = `Bearer ${authToken}`;
        }

        try {
            const response = await fetch(url, config);
            const data = await response.json();

            if (!response.ok) {
                throw new Error(data.error || 'Request failed');
            }

            return data;
        } catch (error) {
            console.error('API request failed:', error);
            throw error;
        }
    }

    static async get(endpoint) {
        return this.request(endpoint);
    }

    static async post(endpoint, data) {
        return this.request(endpoint, {
            method: 'POST',
            body: JSON.stringify(data)
        });
    }

    static async put(endpoint, data) {
        return this.request(endpoint, {
            method: 'PUT',
            body: JSON.stringify(data)
        });
    }

    static async delete(endpoint) {
        return this.request(endpoint, {
            method: 'DELETE'
        });
    }
}

// Authentication API
class AuthAPI {
    static async login(email, password) {
        const response = await API.post('/auth/login', { email, password });
        if (response.access_token) {
            authToken = response.access_token;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('user', JSON.stringify(response.user));
        }
        return response;
    }

    static async register(userData) {
        const response = await API.post('/auth/register', userData);
        if (response.access_token) {
            authToken = response.access_token;
            localStorage.setItem('authToken', authToken);
            localStorage.setItem('user', JSON.stringify(response.user));
        }
        return response;
    }

    static async logout() {
        try {
            await API.post('/auth/logout');
        } catch (error) {
            console.error('Logout error:', error);
        } finally {
            authToken = null;
            localStorage.removeItem('authToken');
            localStorage.removeItem('user');
        }
    }

    static async getProfile() {
        return API.get('/auth/profile');
    }

    static getCurrentUser() {
        const userStr = localStorage.getItem('user');
        return userStr ? JSON.parse(userStr) : null;
    }

    static isAuthenticated() {
        return !!authToken;
    }
}

// Emergency API
class EmergencyAPI {
    static async getEmergencies(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return API.get(`/emergencies${queryString ? '?' + queryString : ''}`);
    }

    static async createEmergency(emergencyData) {
        return API.post('/emergencies', emergencyData);
    }

    static async getEmergency(id) {
        return API.get(`/emergencies/${id}`);
    }

    static async updateEmergency(id, updateData) {
        return API.put(`/emergencies/${id}/update`, updateData);
    }

    static async escalateEmergency(id) {
        return API.post(`/emergencies/${id}/escalate`);
    }

    static async completeEmergency(id) {
        return API.post(`/emergencies/${id}/complete`);
    }

    static async cancelEmergency(id) {
        return API.post(`/emergencies/${id}/cancel`);
    }
}

// Assignment API
class AssignmentAPI {
    static async getAssignments(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return API.get(`/assignments${queryString ? '?' + queryString : ''}`);
    }

    static async acceptAssignment(id, notes = '') {
        return API.post(`/assignments/${id}/accept`, { notes });
    }

    static async declineAssignment(id, notes = '') {
        return API.post(`/assignments/${id}/decline`, { notes });
    }

    static async completeAssignment(id, notes = '') {
        return API.post(`/assignments/${id}/complete`, { notes });
    }
}

// Skills API
class SkillsAPI {
    static async getAllSkills(category = '') {
        const params = category ? { category } : {};
        const queryString = new URLSearchParams(params).toString();
        return API.get(`/skills${queryString ? '?' + queryString : ''}`);
    }

    static async getSkillCategories() {
        return API.get('/skills/categories');
    }
}

// Volunteer API
class VolunteerAPI {
    static async getProfile() {
        return API.get('/volunteers/profile');
    }

    static async updateProfile(profileData) {
        return API.put('/volunteers/profile', profileData);
    }

    static async updateAvailability(status) {
        return API.put('/volunteers/availability', { status });
    }

    static async getSkills() {
        return API.get('/volunteers/skills');
    }

    static async addSkill(skillId) {
        return API.post('/volunteers/skills', { skill_id: skillId });
    }

    static async removeSkill(skillId) {
        return API.delete(`/volunteers/skills/${skillId}`);
    }

    static async getAssignments(status = '') {
        const params = status ? { status } : {};
        return API.get('/volunteers/assignments', params);
    }

    static async respondToAssignment(assignmentId, response, notes = '') {
        return API.put(`/volunteers/assignments/${assignmentId}/respond`, {
            response,
            notes
        });
    }

    static async completeAssignment(assignmentId, notes = '') {
        return API.put(`/volunteers/assignments/${assignmentId}/complete`, { notes });
    }

    static async getInterests() {
        return API.get('/volunteers/interests');
    }

    static async updateInterests(interests) {
        return API.put('/volunteers/interests', { interests });
    }

    static async getLanguages() {
        return API.get('/volunteers/languages');
    }

    static async updateLanguages(languages) {
        return API.put('/volunteers/languages', { languages });
    }

    static async updateExperience(experienceLevel) {
        return API.put('/volunteers/experience', { experience_level: experienceLevel });
    }

    static async updateEmergencyContact(name, phone) {
        return API.put('/volunteers/emergency-contact', { name, phone });
    }

    static async getNearbyEmergencies(radius = 25) {
        return API.get(`/volunteers/nearby-emergencies?radius=${radius}`);
    }

    static async getStats() {
        return API.get('/volunteers/stats');
    }
}

// Admin API
class AdminAPI {
    static async getUsers(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return API.get(`/admin/users${queryString ? '?' + queryString : ''}`);
    }

    static async getSkillVerifications(params = {}) {
        const queryString = new URLSearchParams(params).toString();
        return API.get(`/admin/skill-verifications${queryString ? '?' + queryString : ''}`);
    }

    static async approveSkillVerification(id, notes = '') {
        return API.post(`/admin/skill-verifications/${id}/approve`, { notes });
    }

    static async rejectSkillVerification(id, notes = '') {
        return API.post(`/admin/skill-verifications/${id}/reject`, { notes });
    }
}

// System API
class SystemAPI {
    static async healthCheck() {
        return API.get('/system/health');
    }

    static async getStats() {
        return API.get('/system/stats');
    }
}

// Add Authority API class
class AuthorityAPI {
    static async getDashboardStats() {
        return API.get('/authority/dashboard/stats');
    }

    static async getEmergencies(params = {}) {
        return EmergencyAPI.getEmergencies(params);
    }

    static async createEmergency(emergencyData) {
        return EmergencyAPI.createEmergency(emergencyData);
    }

    static async updateEmergency(id, updateData) {
        return EmergencyAPI.updateEmergency(id, updateData);
    }

    static async completeEmergency(id) {
        return EmergencyAPI.completeEmergency(id);
    }

    static async cancelEmergency(id) {
        return EmergencyAPI.cancelEmergency(id);
    }

    static async escalateEmergency(id) {
        return EmergencyAPI.escalateEmergency(id);
    }
}

// Export APIs
window.API = API;
window.AuthAPI = AuthAPI;
window.EmergencyAPI = EmergencyAPI;
window.AssignmentAPI = AssignmentAPI;
window.SkillsAPI = SkillsAPI;
window.VolunteerAPI = VolunteerAPI;
window.AuthorityAPI = AuthorityAPI;
window.AdminAPI = AdminAPI;
window.SystemAPI = SystemAPI;