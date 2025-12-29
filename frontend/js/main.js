// Main Application JavaScript
document.addEventListener('DOMContentLoaded', function() {
    initializeApp();
});

function initializeApp() {
    // Check if we're on a page that uses the API
    if (typeof AuthAPI !== 'undefined') {
        // Check if user is already logged in
        if (AuthAPI.isAuthenticated()) {
            showDashboard();
        } else {
            showWelcome();
        }
    }
}

function showWelcome() {
    hideAllScreens();
    const welcomeScreen = document.getElementById('welcomeScreen');
    if (welcomeScreen) {
        welcomeScreen.style.display = 'block';
    }
}

function showLogin() {
    hideAllScreens();
    document.getElementById('loginForm').style.display = 'block';
}

function showRegister() {
    hideAllScreens();
    document.getElementById('registerForm').style.display = 'block';
}

function hideAuth() {
    hideAllScreens();
    showWelcome();
}

function hideAllScreens() {
    const screens = ['welcomeScreen', 'loginForm', 'registerForm', 'dashboard'];
    screens.forEach(screenId => {
        const element = document.getElementById(screenId);
        if (element) {
            element.style.display = 'none';
        }
    });
}

function showDashboard() {
    hideAllScreens();
    document.getElementById('dashboard').style.display = 'block';
    
    const user = AuthAPI.getCurrentUser();
    if (user) {
        document.getElementById('dashboardTitle').textContent = `${user.role.charAt(0).toUpperCase() + user.role.slice(1)} Dashboard`;
        loadDashboardContent(user.role);
    }
}

function loadDashboardContent(role) {
    const content = document.getElementById('dashboardContent');
    
    switch (role) {
        case 'volunteer':
            loadVolunteerDashboard(content);
            break;
        case 'authority':
            loadAuthorityDashboard(content);
            break;
        case 'admin':
            loadAdminDashboard(content);
            break;
    }
}

function loadVolunteerDashboard(container) {
    container.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>My Assignments</h5>
                    </div>
                    <div class="card-body">
                        <div id="volunteerAssignments">Loading...</div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>My Skills</h5>
                    </div>
                    <div class="card-body">
                        <div id="volunteerSkills">Loading...</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    loadVolunteerAssignments();
    loadVolunteerSkills();
}

function loadAuthorityDashboard(container) {
    container.innerHTML = `
        <div class="row">
            <div class="col-12 mb-3">
                <button class="btn btn-primary" onclick="showCreateEmergency()">Create Emergency</button>
            </div>
            <div class="col-12">
                <div class="card">
                    <div class="card-header">
                        <h5>My Emergency Requests</h5>
                    </div>
                    <div class="card-body">
                        <div id="authorityEmergencies">Loading...</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    loadAuthorityEmergencies();
}

function loadAdminDashboard(container) {
    container.innerHTML = `
        <div class="row">
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>Skill Verifications</h5>
                    </div>
                    <div class="card-body">
                        <div id="skillVerifications">Loading...</div>
                    </div>
                </div>
            </div>
            <div class="col-md-6">
                <div class="card">
                    <div class="card-header">
                        <h5>System Stats</h5>
                    </div>
                    <div class="card-body">
                        <div id="systemStats">Loading...</div>
                    </div>
                </div>
            </div>
        </div>
    `;
    
    loadSkillVerifications();
    loadSystemStats();
}

// Event Handlers
const loginForm = document.getElementById('loginFormElement');
if (loginForm) {
    loginForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const email = document.getElementById('loginEmail').value;
        const password = document.getElementById('loginPassword').value;
        
        try {
            await AuthAPI.login(email, password);
            showDashboard();
            showAlert('Login successful!', 'success');
        } catch (error) {
            showAlert('Login failed: ' + error.message, 'danger');
        }
    });
}

const registerForm = document.getElementById('registerFormElement');
if (registerForm) {
    registerForm.addEventListener('submit', async function(e) {
        e.preventDefault();
        
        const userData = {
            email: document.getElementById('registerEmail').value,
            password: document.getElementById('registerPassword').value,
            first_name: document.getElementById('registerFirstName').value,
            last_name: document.getElementById('registerLastName').value,
            role: document.getElementById('registerRole').value,
            phone: document.getElementById('registerPhone').value
        };
        
        try {
            await AuthAPI.register(userData);
            showDashboard();
            showAlert('Registration successful!', 'success');
        } catch (error) {
            showAlert('Registration failed: ' + error.message, 'danger');
        }
    });
}

async function logout() {
    try {
        await AuthAPI.logout();
        showWelcome();
        showAlert('Logged out successfully!', 'info');
    } catch (error) {
        showAlert('Logout error: ' + error.message, 'warning');
    }
}

// Dashboard Loading Functions
async function loadVolunteerAssignments() {
    try {
        const response = await VolunteerAPI.getAssignments();
        const container = document.getElementById('volunteerAssignments');
        
        if (response.data.assignments.length === 0) {
            container.innerHTML = '<p>No assignments yet.</p>';
            return;
        }
        
        container.innerHTML = response.data.assignments.map(assignment => `
            <div class="border-bottom pb-2 mb-2">
                <h6>${assignment.emergency.title}</h6>
                <p class="small text-muted">${assignment.emergency.description}</p>
                <span class="badge bg-${getStatusColor(assignment.status)}">${assignment.status}</span>
                ${assignment.status === 'requested' ? `
                    <div class="mt-2">
                        <button class="btn btn-sm btn-success" onclick="respondToAssignment(${assignment.id}, 'accepted')">Accept</button>
                        <button class="btn btn-sm btn-secondary" onclick="respondToAssignment(${assignment.id}, 'declined')">Decline</button>
                    </div>
                ` : ''}
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('volunteerAssignments').innerHTML = '<p class="text-danger">Error loading assignments</p>';
    }
}

async function loadVolunteerSkills() {
    try {
        const response = await VolunteerAPI.getSkills();
        const container = document.getElementById('volunteerSkills');
        
        if (response.data.skills.length === 0) {
            container.innerHTML = '<p>No skills added yet.</p>';
            return;
        }
        
        container.innerHTML = response.data.skills.map(skill => `
            <div class="border-bottom pb-2 mb-2">
                <h6>${skill.skill.name}</h6>
                <span class="badge bg-${getVerificationColor(skill.verification_status)}">${skill.verification_status}</span>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('volunteerSkills').innerHTML = '<p class="text-danger">Error loading skills</p>';
    }
}

async function loadAuthorityEmergencies() {
    try {
        const response = await EmergencyAPI.getEmergencies();
        const container = document.getElementById('authorityEmergencies');
        
        if (response.data.emergencies.length === 0) {
            container.innerHTML = '<p>No emergency requests yet.</p>';
            return;
        }
        
        container.innerHTML = response.data.emergencies.map(emergency => `
            <div class="border-bottom pb-2 mb-2">
                <h6>${emergency.title}</h6>
                <p class="small text-muted">${emergency.description}</p>
                <span class="badge bg-${getPriorityColor(emergency.priority_level)}">${emergency.priority_level}</span>
                <span class="badge bg-${getStatusColor(emergency.status)}">${emergency.status}</span>
                <p class="small">Volunteers needed: ${emergency.volunteers_needed}</p>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('authorityEmergencies').innerHTML = '<p class="text-danger">Error loading emergencies</p>';
    }
}

async function loadSkillVerifications() {
    try {
        const response = await AdminAPI.getSkillVerifications();
        const container = document.getElementById('skillVerifications');
        
        if (response.data.verifications.length === 0) {
            container.innerHTML = '<p>No pending verifications.</p>';
            return;
        }
        
        container.innerHTML = response.data.verifications.map(verification => `
            <div class="border-bottom pb-2 mb-2">
                <h6>${verification.skill.name}</h6>
                <p class="small">Volunteer: ${verification.volunteer.user.first_name} ${verification.volunteer.user.last_name}</p>
                <div class="mt-2">
                    <button class="btn btn-sm btn-success" onclick="approveSkill(${verification.id})">Approve</button>
                    <button class="btn btn-sm btn-danger" onclick="rejectSkill(${verification.id})">Reject</button>
                </div>
            </div>
        `).join('');
    } catch (error) {
        document.getElementById('skillVerifications').innerHTML = '<p class="text-danger">Error loading verifications</p>';
    }
}

async function loadSystemStats() {
    try {
        const response = await SystemAPI.getStats();
        const container = document.getElementById('systemStats');
        
        container.innerHTML = `
            <div class="row">
                <div class="col-6"><strong>Total Users:</strong> ${response.data.total_users}</div>
                <div class="col-6"><strong>Volunteers:</strong> ${response.data.total_volunteers}</div>
                <div class="col-6"><strong>Authorities:</strong> ${response.data.total_authorities}</div>
                <div class="col-6"><strong>Open Emergencies:</strong> ${response.data.open_emergencies}</div>
            </div>
        `;
    } catch (error) {
        document.getElementById('systemStats').innerHTML = '<p class="text-danger">Error loading stats</p>';
    }
}

// Helper Functions
function getStatusColor(status) {
    const colors = {
        'requested': 'warning',
        'accepted': 'primary',
        'declined': 'secondary',
        'completed': 'success',
        'cancelled': 'danger',
        'open': 'warning',
        'assigned': 'primary',
        'closed': 'success'
    };
    return colors[status] || 'secondary';
}

function getVerificationColor(status) {
    const colors = {
        'pending': 'warning',
        'verified': 'success',
        'rejected': 'danger'
    };
    return colors[status] || 'secondary';
}

function getPriorityColor(priority) {
    const colors = {
        'low': 'secondary',
        'medium': 'primary',
        'high': 'warning',
        'critical': 'danger'
    };
    return colors[priority] || 'secondary';
}

function showAlert(message, type) {
    const alertDiv = document.createElement('div');
    alertDiv.className = `alert alert-${type} alert-dismissible fade show`;
    alertDiv.innerHTML = `
        ${message}
        <button type="button" class="btn-close" data-bs-dismiss="alert"></button>
    `;
    
    document.body.insertBefore(alertDiv, document.body.firstChild);
    
    setTimeout(() => {
        if (alertDiv.parentNode) {
            alertDiv.remove();
        }
    }, 5000);
}

// Action Functions
async function respondToAssignment(assignmentId, response) {
    try {
        await VolunteerAPI.respondToAssignment(assignmentId, response);
        showAlert(`Assignment ${response} successfully!`, 'success');
        loadVolunteerAssignments();
    } catch (error) {
        showAlert('Error responding to assignment: ' + error.message, 'danger');
    }
}

async function approveSkill(verificationId) {
    try {
        await AdminAPI.approveSkillVerification(verificationId);
        showAlert('Skill approved successfully!', 'success');
        loadSkillVerifications();
    } catch (error) {
        showAlert('Error approving skill: ' + error.message, 'danger');
    }
}

async function rejectSkill(verificationId) {
    try {
        await AdminAPI.rejectSkillVerification(verificationId);
        showAlert('Skill rejected successfully!', 'success');
        loadSkillVerifications();
    } catch (error) {
        showAlert('Error rejecting skill: ' + error.message, 'danger');
    }
}