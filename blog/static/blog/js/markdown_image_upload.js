document.addEventListener('DOMContentLoaded', function() {
    const textareaElement = document.querySelector('.markdownx-editor');
    if (!textareaElement) return;
    
    // Создаем кнопку загрузки изображений
    const uploadButton = document.createElement('button');
    uploadButton.type = 'button';
    uploadButton.className = 'btn btn-sm btn-outline-secondary mt-2 mb-2';
    uploadButton.innerHTML = '<i class="bi bi-image"></i> Загрузить изображение';
    
    // Создаем скрытый input для выбора файла
    const fileInput = document.createElement('input');
    fileInput.type = 'file';
    fileInput.accept = 'image/*';
    fileInput.style.display = 'none';
    fileInput.addEventListener('change', function() {
        if (this.files && this.files[0]) {
            const formData = new FormData();
            formData.append('image', this.files[0]);
            
            // Отправляем запрос на загрузку
            fetch('/markdownx/upload/', {
                method: 'POST',
                body: formData,
                headers: {
                    'X-CSRFToken': getCookie('csrftoken')
                }
            })
            .then(response => response.json())
            .then(data => {
                // Вставляем разметку изображения в текстовое поле
                const imageMarkdown = `![${this.files[0].name}](${data.image_path})`;
                const textarea = document.querySelector('.markdownx-editor');
                const startPos = textarea.selectionStart;
                const endPos = textarea.selectionEnd;
                const text = textarea.value;
                
                textarea.value = text.substring(0, startPos) + imageMarkdown + text.substring(endPos);
                textarea.focus();
                textarea.selectionStart = textarea.selectionEnd = startPos + imageMarkdown.length;
                
                // Вызываем событие изменения для обновления предпросмотра
                const event = new Event('input', { bubbles: true });
                textarea.dispatchEvent(event);
            })
            .catch(error => console.error('Ошибка загрузки изображения:', error));
        }
    });
    
    // Функция для получения CSRF токена
    function getCookie(name) {
        let cookieValue = null;
        if (document.cookie && document.cookie !== '') {
            const cookies = document.cookie.split(';');
            for (let i = 0; i < cookies.length; i++) {
                const cookie = cookies[i].trim();
                if (cookie.substring(0, name.length + 1) === (name + '=')) {
                    cookieValue = decodeURIComponent(cookie.substring(name.length + 1));
                    break;
                }
            }
        }
        return cookieValue;
    }
    
    // Добавляем элементы в DOM
    uploadButton.addEventListener('click', () => fileInput.click());
    const textareaParent = textareaElement.parentElement;
    textareaParent.insertBefore(uploadButton, textareaElement);
    textareaParent.insertBefore(fileInput, textareaElement);
});