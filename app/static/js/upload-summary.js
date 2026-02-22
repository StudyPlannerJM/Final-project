// Upload Summary - File upload and drag-drop handler
document.addEventListener('DOMContentLoaded', function() {
    const fileInput = document.getElementById('file');
    const dropZone = document.getElementById('dropZone');
    const fileSelected = document.getElementById('fileSelected');
    const fileName = document.getElementById('fileName');
    const removeFile = document.getElementById('removeFile');
    const ocrOption = document.getElementById('ocrOption');
    const uploadForm = document.getElementById('uploadForm');
    const submitBtn = document.getElementById('submitBtn');
    
    // Handle file selection
    fileInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            showSelectedFile(this.files[0]);
        }
    });
    
    // Handle drag and drop
    dropZone.addEventListener('dragover', function(e) {
        e.preventDefault();
        this.classList.add('drag-over');
    });
    
    dropZone.addEventListener('dragleave', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
    });
    
    dropZone.addEventListener('drop', function(e) {
        e.preventDefault();
        this.classList.remove('drag-over');
        
        if (e.dataTransfer.files && e.dataTransfer.files[0]) {
            fileInput.files = e.dataTransfer.files;
            showSelectedFile(e.dataTransfer.files[0]);
        }
    });
    
    // Show selected file
    function showSelectedFile(file) {
        fileName.textContent = file.name;
        dropZone.querySelector('.file-upload-content').style.display = 'none';
        fileSelected.style.display = 'flex';
        
        // Show OCR option for PDF files
        if (file.name.toLowerCase().endsWith('.pdf')) {
            ocrOption.style.display = 'block';
        } else {
            ocrOption.style.display = 'none';
        }
    }
    
    // Remove selected file
    removeFile.addEventListener('click', function() {
        fileInput.value = '';
        dropZone.querySelector('.file-upload-content').style.display = 'flex';
        fileSelected.style.display = 'none';
        ocrOption.style.display = 'none';
    });
    
    // Handle form submission
    uploadForm.addEventListener('submit', function() {
        submitBtn.disabled = true;
        submitBtn.innerHTML = '<i class="fas fa-spinner fa-spin"></i> Processing...';
    });
});
