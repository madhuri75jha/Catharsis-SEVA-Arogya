/**
 * Bedrock Prescription Form - Dynamic Form Rendering
 * Handles dynamic form generation based on hospital configuration
 */

let currentConfig = null;
let currentData = null;
let repeatableSectionCounters = {};

/**
 * Normalize backend PrescriptionData into the shape expected by renderer:
 * {
 *   sections: {
 *     patient_details: { field: value, field_data: {confidence, source_text}, ... },
 *     medications: [{...}, {...}]
 *   }
 * }
 * @param {object|null} prescriptionData
 * @returns {object|null}
 */
function normalizePrescriptionData(prescriptionData) {
    if (!prescriptionData || !Array.isArray(prescriptionData.sections)) {
        return null;
    }

    const normalized = { sections: {} };

    prescriptionData.sections.forEach((section) => {
        if (!section || !section.section_id || !Array.isArray(section.fields)) {
            return;
        }

        const match = /^(.+)_([0-9]+)$/.exec(section.section_id);
        const baseSectionId = match ? match[1] : section.section_id;
        const repeatIndex = match ? parseInt(match[2], 10) : null;

        const fieldMap = {};
        section.fields.forEach((field) => {
            if (!field || !field.field_name) return;
            fieldMap[field.field_name] = field.value ?? '';
            fieldMap[`${field.field_name}_data`] = {
                confidence: field.confidence,
                source_text: field.source_text || null
            };
        });

        if (repeatIndex !== null) {
            if (!Array.isArray(normalized.sections[baseSectionId])) {
                normalized.sections[baseSectionId] = [];
            }
            normalized.sections[baseSectionId][repeatIndex] = fieldMap;
        } else {
            normalized.sections[baseSectionId] = fieldMap;
        }
    });

    // Remove sparse array holes if any indexes were skipped.
    Object.keys(normalized.sections).forEach((key) => {
        if (Array.isArray(normalized.sections[key])) {
            normalized.sections[key] = normalized.sections[key].filter(Boolean);
        }
    });

    return normalized;
}

/**
 * Initialize the prescription form
 * @param {string} hospitalId - Hospital identifier
 * @param {object} prescriptionData - Extracted prescription data (optional)
 */
async function initializePrescriptionForm(hospitalId, prescriptionData) {
    try {
        // Show loading state
        showLoading();
        
        // Load hospital configuration
        currentConfig = await loadHospitalConfiguration(hospitalId);
        currentData = normalizePrescriptionData(prescriptionData);
        
        // Update hospital name
        if (currentConfig.hospital_name) {
            document.getElementById('hospitalName').textContent = currentConfig.hospital_name;
        }
        
        // Render form sections
        renderFormSections(currentConfig, currentData);
        
        // Show form
        hideLoading();
        showForm();
        
    } catch (error) {
        console.error('Failed to initialize form:', error);
        showError(error.message || 'Failed to load configuration');
    }
}

/**
 * Load hospital configuration from API
 * @param {string} hospitalId - Hospital identifier
 * @returns {Promise<object>} Hospital configuration
 */
async function loadHospitalConfiguration(hospitalId) {
    const response = await fetch(`/api/v1/config/${hospitalId}`);
    
    if (!response.ok) {
        throw new Error(`Failed to load configuration: ${response.statusText}`);
    }
    
    return await response.json();
}

/**
 * Render all form sections based on configuration
 * @param {object} config - Hospital configuration
 * @param {object} data - Prescription data (optional)
 */
function renderFormSections(config, data) {
    const container = document.getElementById('dynamicSections');
    container.innerHTML = '';
    
    // Sort sections by display_order
    const sections = [...config.sections].sort((a, b) => a.display_order - b.display_order);
    
    sections.forEach(section => {
        const sectionElement = createSectionElement(section, data);
        container.appendChild(sectionElement);
    });
}

/**
 * Create a section element
 * @param {object} section - Section configuration
 * @param {object} data - Prescription data (optional)
 * @returns {HTMLElement} Section element
 */
function createSectionElement(section, data) {
    const sectionDiv = document.createElement('div');
    sectionDiv.className = 'mb-6';
    sectionDiv.id = `section-${section.section_id}`;
    
    // Section header
    const header = document.createElement('div');
    header.className = 'flex justify-between items-center mb-2';
    
    const title = document.createElement('h3');
    title.className = 'text-primary text-xs font-bold uppercase tracking-wider';
    title.textContent = section.section_label;
    header.appendChild(title);
    
    // Add button for repeatable sections
    if (section.repeatable) {
        const addButton = document.createElement('button');
        addButton.className = 'bg-primary/10 text-primary rounded-full px-3 py-1 text-xs font-bold flex items-center gap-1';
        addButton.innerHTML = '<span class="material-symbols-outlined text-xs">add</span> Add';
        addButton.onclick = () => addRepeatableSection(section);
        header.appendChild(addButton);
        
        // Initialize counter
        repeatableSectionCounters[section.section_id] = 0;
    }
    
    sectionDiv.appendChild(header);
    
    // Section content container
    const contentContainer = document.createElement('div');
    contentContainer.id = `${section.section_id}-container`;
    
    if (section.repeatable) {
        // For repeatable sections, add instances based on data
        const sectionData = data?.sections?.[section.section_id];
        if (sectionData && Array.isArray(sectionData) && sectionData.length > 0) {
            sectionData.forEach((instanceData, index) => {
                const instance = createRepeatableSectionInstance(section, index, instanceData);
                contentContainer.appendChild(instance);
                repeatableSectionCounters[section.section_id] = index + 1;
            });
        } else {
            // Add one empty instance
            const instance = createRepeatableSectionInstance(section, 0, null);
            contentContainer.appendChild(instance);
            repeatableSectionCounters[section.section_id] = 1;
        }
    } else {
        // For non-repeatable sections, render fields directly
        const fieldsContainer = createFieldsContainer(section, data?.sections?.[section.section_id]);
        contentContainer.appendChild(fieldsContainer);
    }
    
    sectionDiv.appendChild(contentContainer);
    
    return sectionDiv;
}

/**
 * Create a repeatable section instance
 * @param {object} section - Section configuration
 * @param {number} index - Instance index
 * @param {object} data - Instance data (optional)
 * @returns {HTMLElement} Instance element
 */
function createRepeatableSectionInstance(section, index, data) {
    const instanceDiv = document.createElement('div');
    instanceDiv.className = 'mb-4 p-4 bg-slate-50 dark:bg-slate-800/50 rounded-lg border border-slate-200 dark:border-slate-700 relative';
    instanceDiv.id = `${section.section_id}-instance-${index}`;
    
    // Remove button
    if (index > 0 || repeatableSectionCounters[section.section_id] > 1) {
        const removeButton = document.createElement('button');
        removeButton.className = 'absolute top-2 right-2 text-red-500 hover:text-red-700';
        removeButton.innerHTML = '<span class="material-symbols-outlined text-sm">close</span>';
        removeButton.onclick = () => removeRepeatableInstance(section.section_id, index);
        instanceDiv.appendChild(removeButton);
    }
    
    // Fields
    const fieldsContainer = createFieldsContainer(section, data, index);
    instanceDiv.appendChild(fieldsContainer);
    
    return instanceDiv;
}

/**
 * Create fields container
 * @param {object} section - Section configuration
 * @param {object} data - Section data (optional)
 * @param {number} instanceIndex - Instance index for repeatable sections
 * @returns {HTMLElement} Fields container
 */
function createFieldsContainer(section, data, instanceIndex = null) {
    const container = document.createElement('div');
    
    // Determine grid layout based on section type
    if (section.section_id === 'vitals') {
        container.className = 'flex justify-between gap-2';
    } else if (section.section_id === 'patient_details') {
        container.className = 'grid grid-cols-2 gap-y-3 gap-x-4';
    } else {
        container.className = 'space-y-3';
    }
    
    // Sort fields by display_order
    const fields = [...section.fields].sort((a, b) => a.display_order - b.display_order);
    
    fields.forEach(field => {
        const fieldElement = createFieldElement(field, data, section.section_id, instanceIndex);
        container.appendChild(fieldElement);
    });
    
    return container;
}

/**
 * Create a field element
 * @param {object} field - Field configuration
 * @param {object} data - Field data (optional)
 * @param {string} sectionId - Section identifier
 * @param {number} instanceIndex - Instance index for repeatable sections
 * @returns {HTMLElement} Field element
 */
function createFieldElement(field, data, sectionId, instanceIndex) {
    const fieldDiv = document.createElement('div');
    
    // Special styling for vitals
    if (sectionId === 'vitals') {
        fieldDiv.className = 'flex-1 bg-white dark:bg-slate-900 p-3 rounded-lg border border-slate-200 dark:border-slate-700';
    } else {
        fieldDiv.className = 'flex flex-col';
    }
    
    // Field label
    const label = document.createElement('label');
    label.className = 'text-slate-400 text-[10px] uppercase font-bold mb-1 flex items-center gap-1';
    label.textContent = field.display_label;
    
    if (field.required) {
        const required = document.createElement('span');
        required.className = 'text-red-500';
        required.textContent = '*';
        label.appendChild(required);
    }
    
    fieldDiv.appendChild(label);
    
    // Get field value and confidence
    const fieldValue = data?.[field.field_name];
    const fieldData = data?.[`${field.field_name}_data`];
    const confidence = fieldData?.confidence;
    const sourceText = fieldData?.source_text;
    
    // Create input element
    const inputContainer = document.createElement('div');
    inputContainer.className = 'relative';
    
    const input = createInputElement(field, fieldValue, sectionId, instanceIndex);
    
    // Apply confidence styling if auto-filled
    if (confidence !== undefined) {
        applyConfidenceIndicator(input, confidence);
        input.dataset.autofilled = 'true';
        input.dataset.confidence = confidence;
        
        // Add info icon for source context
        if (sourceText) {
            const infoIcon = document.createElement('button');
            infoIcon.className = 'absolute right-2 top-1/2 -translate-y-1/2 text-slate-400 hover:text-primary';
            infoIcon.innerHTML = '<span class="material-symbols-outlined text-sm">info</span>';
            infoIcon.onclick = () => showSourceContext(field.display_label, sourceText, confidence);
            infoIcon.type = 'button';
            inputContainer.appendChild(infoIcon);
        }
    }
    
    inputContainer.appendChild(input);
    fieldDiv.appendChild(inputContainer);
    
    return fieldDiv;
}

/**
 * Create input element based on field type
 * @param {object} field - Field configuration
 * @param {any} value - Field value
 * @param {string} sectionId - Section identifier
 * @param {number} instanceIndex - Instance index for repeatable sections
 * @returns {HTMLElement} Input element
 */
function createInputElement(field, value, sectionId, instanceIndex) {
    let input;
    const fieldId = instanceIndex !== null 
        ? `${sectionId}-${instanceIndex}-${field.field_name}`
        : `${sectionId}-${field.field_name}`;
    
    switch (field.field_type) {
        case 'multiline':
            input = document.createElement('textarea');
            input.rows = field.rows || 4;
            input.className = 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none resize-none';
            break;
            
        case 'dropdown':
            input = document.createElement('select');
            input.className = 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-slate-800 dark:text-slate-100 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none';
            
            // Add empty option
            const emptyOption = document.createElement('option');
            emptyOption.value = '';
            emptyOption.textContent = '-- Select --';
            input.appendChild(emptyOption);
            
            // Add options
            field.options?.forEach(option => {
                const optionElement = document.createElement('option');
                optionElement.value = option;
                optionElement.textContent = option;
                input.appendChild(optionElement);
            });
            break;
            
        case 'number':
            input = document.createElement('input');
            input.type = 'number';
            input.className = 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none';
            if (field.min_value !== undefined) input.min = field.min_value;
            if (field.max_value !== undefined) input.max = field.max_value;
            break;
            
        default: // text
            input = document.createElement('input');
            input.type = 'text';
            input.className = 'w-full bg-slate-50 dark:bg-slate-900 border border-slate-200 dark:border-slate-700 rounded-lg py-2 px-3 text-sm text-slate-800 dark:text-slate-100 placeholder-slate-400 focus:ring-2 focus:ring-primary/20 focus:border-primary transition-all outline-none';
            if (field.max_length) input.maxLength = field.max_length;
    }
    
    input.id = fieldId;
    input.name = fieldId;
    input.placeholder = field.placeholder || '';
    
    if (value !== undefined && value !== null) {
        input.value = value;
    }
    
    if (field.required) {
        input.required = true;
    }
    
    return input;
}

/**
 * Apply confidence indicator styling to input
 * @param {HTMLElement} input - Input element
 * @param {number} confidence - Confidence score (0-1)
 */
function applyConfidenceIndicator(input, confidence) {
    // Remove existing confidence classes
    input.classList.remove('border-green-500', 'border-yellow-500', 'border-red-500', 'ring-green-100', 'ring-yellow-100', 'ring-red-100');
    
    if (confidence >= 0.8) {
        // High confidence - green
        input.classList.add('border-green-500', 'ring-2', 'ring-green-100', 'dark:ring-green-900/30');
    } else if (confidence >= 0.5) {
        // Medium confidence - yellow
        input.classList.add('border-yellow-500', 'ring-2', 'ring-yellow-100', 'dark:ring-yellow-900/30');
    } else {
        // Low confidence - red
        input.classList.add('border-red-500', 'ring-2', 'ring-red-100', 'dark:ring-red-900/30');
    }
}

/**
 * Show source context modal
 * @param {string} fieldLabel - Field label
 * @param {string} sourceText - Source text from transcript
 * @param {number} confidence - Confidence score
 */
function showSourceContext(fieldLabel, sourceText, confidence) {
    const modal = document.getElementById('contextModal');
    const content = document.getElementById('contextContent');
    
    const confidencePercent = Math.round(confidence * 100);
    const confidenceClass = confidence >= 0.8 ? 'text-green-600' : confidence >= 0.5 ? 'text-yellow-600' : 'text-red-600';
    
    content.innerHTML = `
        <div class="mb-4">
            <h4 class="font-bold text-slate-900 dark:text-white mb-1">${fieldLabel}</h4>
            <p class="text-xs ${confidenceClass}">Confidence: ${confidencePercent}%</p>
        </div>
        <div class="bg-slate-100 dark:bg-slate-800 p-3 rounded-lg">
            <p class="text-xs text-slate-500 dark:text-slate-400 mb-1">Source from transcript:</p>
            <p class="italic">"${sourceText}"</p>
        </div>
    `;
    
    modal.classList.remove('hidden');
}

/**
 * Add a new repeatable section instance
 * @param {object} section - Section configuration
 */
function addRepeatableSection(section) {
    const container = document.getElementById(`${section.section_id}-container`);
    const index = repeatableSectionCounters[section.section_id];
    
    const instance = createRepeatableSectionInstance(section, index, null);
    container.appendChild(instance);
    
    repeatableSectionCounters[section.section_id]++;
}

/**
 * Remove a repeatable section instance
 * @param {string} sectionId - Section identifier
 * @param {number} index - Instance index
 */
function removeRepeatableInstance(sectionId, index) {
    const instance = document.getElementById(`${sectionId}-instance-${index}`);
    if (instance) {
        instance.remove();
    }
}

/**
 * Show loading state
 */
function showLoading() {
    document.getElementById('loadingState').classList.remove('hidden');
    document.getElementById('errorState').classList.add('hidden');
    document.getElementById('formContainer').classList.add('hidden');
    document.getElementById('footerActions').classList.add('hidden');
}

/**
 * Hide loading state
 */
function hideLoading() {
    document.getElementById('loadingState').classList.add('hidden');
}

/**
 * Show form
 */
function showForm() {
    document.getElementById('formContainer').classList.remove('hidden');
    document.getElementById('footerActions').classList.remove('hidden');
}

/**
 * Show error state
 * @param {string} message - Error message
 */
function showError(message) {
    document.getElementById('errorState').classList.remove('hidden');
    document.getElementById('errorMessage').textContent = message;
    document.getElementById('loadingState').classList.add('hidden');
    document.getElementById('formContainer').classList.add('hidden');
    document.getElementById('footerActions').classList.add('hidden');
}
