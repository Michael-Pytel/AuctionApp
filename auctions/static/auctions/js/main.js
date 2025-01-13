// main.js
document.addEventListener('DOMContentLoaded', function() {
    // Utility function for toggle functionality
    function setupToggle(triggerSelector, targetSelector, activeClass = 'active') {
        const trigger = document.querySelector(triggerSelector);
        const target = document.querySelector(targetSelector);

        if (trigger && target) {
            trigger.addEventListener('click', (e) => {
                e.stopPropagation();
                target.classList.toggle(activeClass);

                // Close when clicking outside
                document.addEventListener('click', function closeMenu(e) {
                    if (!target.contains(e.target) && !trigger.contains(e.target)) {
                        target.classList.remove(activeClass);
                        document.removeEventListener('click', closeMenu);
                    }
                });
            });
        }
    }

    // Setup toggles
    setupToggle('.mobile-menu-btn', '.nav-sections');
    setupToggle('.user-menu-btn', '.user-dropdown');

    // Enhanced message system
    const messages = document.querySelectorAll('.message');
    messages.forEach(message => {
        // Auto-dismiss after 5 seconds for success messages
        if (message.classList.contains('success')) {
            setTimeout(() => {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 300);
            }, 5000);
        }

        // Close button functionality
        const closeBtn = message.querySelector('.close-message');
        if (closeBtn) {
            closeBtn.addEventListener('click', () => {
                message.style.opacity = '0';
                setTimeout(() => message.remove(), 300);
            });
        }
    });

    // Enhanced category toggle
    const categoryToggle = document.querySelector('.category-toggle');
    if (categoryToggle) {
        categoryToggle.addEventListener('click', function() {
            const categoriesContainer = document.querySelector('.categories-container');
            const icon = this.querySelector('i');

            if (categoriesContainer && icon) {
                const isActive = categoriesContainer.classList.toggle('active');
                icon.className = isActive ? 'fas fa-times' : 'fas fa-filter';
            }
        });
    }

    // Enhanced comment system
    class CommentSystem {
        constructor() {
            this.wrapper = document.querySelector('.comment-input-wrapper');
            this.input = document.getElementById('commentInput');
            this.submitBtn = document.getElementById('submitComment');
            this.cancelBtn = document.getElementById('cancelComment');
            this.form = document.getElementById('commentForm');

            if (this.input) {
                this.initializeEventListeners();
            }
        }

        initializeEventListeners() {
            // Input focus handling
            this.input.addEventListener('focus', () => {
                this.wrapper.classList.add('active');
                this.adjustTextareaHeight();
            });

            // Input validation and auto-resize
            this.input.addEventListener('input', () => {
                this.submitBtn.disabled = !this.input.value.trim();
                this.adjustTextareaHeight();
                this.validateInput();
            });

            // Cancel button
            this.cancelBtn.addEventListener('click', () => this.resetForm());

            // Form submission
            this.form.addEventListener('submit', (e) => this.handleSubmit(e));

            // Character limit indicator
            const maxLength = this.input.getAttribute('maxlength');
            if (maxLength) {
                this.createCharacterCounter(maxLength);
            }
        }

        adjustTextareaHeight() {
            this.input.style.height = 'auto';
            this.input.style.height = `${this.input.scrollHeight}px`;
        }

        validateInput() {
            const value = this.input.value.trim();
            const isValid = value.length > 0 && value.length <= 500;
            this.submitBtn.disabled = !isValid;
            return isValid;
        }

        resetForm() {
            this.input.value = '';
            this.input.style.height = 'auto';
            this.wrapper.classList.remove('active');
            this.submitBtn.disabled = true;
            if (this.charCounter) {
                this.updateCharacterCounter();
            }
        }

        handleSubmit(e) {
            if (!this.validateInput()) {
                e.preventDefault();
                return false;
            }
        }

        createCharacterCounter(maxLength) {
            this.charCounter = document.createElement('div');
            this.charCounter.className = 'character-counter';
            this.wrapper.appendChild(this.charCounter);
            this.updateCharacterCounter();
        }

        updateCharacterCounter() {
            if (this.charCounter) {
                const remaining = parseInt(this.input.getAttribute('maxlength')) - this.input.value.length;
                this.charCounter.textContent = `${remaining} characters remaining`;
            }
        }
    }

    // Initialize comment system
    new CommentSystem();
});
class PasswordValidator {
    constructor(passwordInput, confirmInput, submitButton) {
        this.passwordInput = passwordInput;
        this.confirmInput = confirmInput;
        this.submitButton = submitButton;
        this.requirements = {
            length: { regex: /.{8,}/, message: 'At least 8 characters long' },
            number: { regex: /\d/, message: 'At least one number' },
            uppercase: { regex: /[A-Z]/, message: 'At least one uppercase letter' },
            lowercase: { regex: /[a-z]/, message: 'At least one lowercase letter' },
            special: { regex: /[^A-Za-z0-9]/, message: 'At least one special character' }
        };

        this.initializeValidation();
    }

    initializeValidation() {
        this.createFeedbackContainer();

        // Add event listeners without modifying the input value
        this.passwordInput.addEventListener('input', () => this.validatePassword());
        if (this.confirmInput) {
            this.confirmInput.addEventListener('input', () => this.validateConfirmation());
        }

        // Add password toggle functionality
        this.setupPasswordToggles();

        // Initial validation state
        this.submitButton.disabled = true;
    }

    setupPasswordToggles() {
        const setupToggle = (input, button) => {
            if (button) {
                button.innerHTML = '<i class="fas fa-eye"></i>';
                button.addEventListener('click', (e) => {
                    e.preventDefault(); // Prevent any form submission
                    const type = input.type === 'password' ? 'text' : 'password';
                    input.type = type;
                    button.innerHTML = `<i class="fas fa-eye${type === 'password' ? '' : '-slash'}"></i>`;
                });
            }
        };

        setupToggle(this.passwordInput, this.passwordInput.nextElementSibling);
        if (this.confirmInput) {
            setupToggle(this.confirmInput, this.confirmInput.nextElementSibling);
        }
    }

    validatePassword() {
        const password = this.passwordInput.value;
        let isValid = true;

        Object.entries(this.requirements).forEach(([key, requirement]) => {
            const requirementElement = document.getElementById(`req-${key}`);
            const icon = requirementElement.querySelector('i');

            const meetsRequirement = requirement.regex.test(password);
            isValid = isValid && meetsRequirement;

            icon.className = meetsRequirement ? 'fas fa-check' : 'fas fa-times';
            icon.style.color = meetsRequirement ? '#22c55e' : '#ef4444';
        });

        // Update submit button state
        this.updateSubmitButtonState(isValid);

        return isValid;
    }

    validateConfirmation() {
        if (!this.confirmInput) return true;

        const password = this.passwordInput.value;
        const confirmation = this.confirmInput.value;
        const matches = password === confirmation;

        const errorMessage = this.confirmInput.parentNode.parentNode.querySelector('.password-match-error');
        if (errorMessage) {
            errorMessage.style.display = confirmation && !matches ? 'block' : 'none';
        }

        this.updateSubmitButtonState(this.validatePassword() && matches);

        return matches;
    }

    updateSubmitButtonState(isValid) {
        if (this.submitButton) {
            const termsCheckbox = document.getElementById('terms');
            const termsChecked = termsCheckbox ? termsCheckbox.checked : true;
            const confirmValid = this.confirmInput ?
                               this.confirmInput.value === this.passwordInput.value :
                               true;

            this.submitButton.disabled = !isValid || !termsChecked || !confirmValid;
        }
    }

    createFeedbackContainer() {
        this.feedbackContainer = document.createElement('div');
        this.feedbackContainer.className = 'password-requirements';

        const requirementsList = document.createElement('ul');

        Object.entries(this.requirements).forEach(([key, requirement]) => {
            const li = document.createElement('li');
            li.id = `req-${key}`;
            li.innerHTML = `
                <i class="fas fa-times"></i>
                <span>${requirement.message}</span>
            `;
            requirementsList.appendChild(li);
        });

        this.feedbackContainer.appendChild(requirementsList);
        this.passwordInput.parentNode.parentNode.appendChild(this.feedbackContainer);
    }
}

// Initialize on DOM load
document.addEventListener('DOMContentLoaded', function() {
    const registerForm = document.getElementById('register-form');
    if (registerForm) {
        const passwordInput = registerForm.querySelector('input[name="password"]');
        const confirmInput = registerForm.querySelector('input[name="confirmation"]');
        const submitButton = registerForm.querySelector('button[type="submit"]');
        const termsCheckbox = document.getElementById('terms');

        if (passwordInput) {
            const validator = new PasswordValidator(passwordInput, confirmInput, submitButton);

            if (termsCheckbox) {
                termsCheckbox.addEventListener('change', () => {
                    validator.validatePassword();
                });
            }
        }
    }
    const resetForm = document.getElementById('password-reset-form');
    if (resetForm) {
        const passwordInput = resetForm.querySelector('input[name="password"]');
        const confirmInput = resetForm.querySelector('input[name="confirmation"]');
        const submitButton = resetForm.querySelector('button[type="submit"]');

        if (passwordInput) {
            new PasswordValidator(passwordInput, confirmInput, submitButton);
        }
    }
});