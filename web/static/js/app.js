// Элементы DOM
const userIdElement = document.getElementById('userId');
const wordsListElement = document.getElementById('wordsList');
const notificationElement = document.getElementById('notification');
const loadingOverlay = document.getElementById('loadingOverlay');
const wordsLoading = document.getElementById('wordsLoading');
const bookmarksHint = document.querySelector('.bookmarks-hint');

// Переменные состояния
let currentUserId = null;

// Инициализация при загрузке
document.addEventListener('DOMContentLoaded', function() {
    // Получаем параметры URL
    const urlParams = new URLSearchParams(window.location.search);
    currentUserId = urlParams.get('user_id');

    if (currentUserId) {
        userIdElement.textContent = currentUserId;
    } else {
        showNotification('Ошибка: Не указан ID пользователя', 'error');
        userIdElement.textContent = 'не определен';
    }

    // Настройка закладок
    setupBookmarks();

    // Назначаем обработчики кнопок
    document.getElementById('addWordBtn').addEventListener('click', addWord);
    document.getElementById('searchBtn').addEventListener('click', findTranslation);
    document.getElementById('refreshWordsBtn').addEventListener('click', loadWords);

    // Обработчик для подсказки закладок
    bookmarksHint.addEventListener('click', function() {
        this.style.display = 'none';
    });

    // Загружаем слова при открытии страницы
    loadWords();
});

// Настройка закладок
function setupBookmarks() {
    const bookmarks = document.querySelectorAll('.bookmark');
    bookmarks.forEach(bookmark => {
        bookmark.addEventListener('click', function() {
            bookmarks.forEach(b => b.classList.remove('active'));
            this.classList.add('active');

            document.querySelectorAll('.page').forEach(page => {
                page.classList.remove('active');
            });

            const pageId = this.getAttribute('data-page');
            document.getElementById(pageId).classList.add('active');

            if (pageId === 'all-words') {
                loadWords();
            }
            if (pageId === 'statistics') {
                loadStatistics();
            }
        });
    });
}

// Загрузка слов пользователя
async function loadWords() {
    if (!currentUserId) return;

    try {
        wordsLoading.style.display = 'flex';
        wordsListElement.innerHTML = '';

        const response = await fetch(`/api/words?user_id=${currentUserId}`);

        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }

        const words = await response.json();

        if (words.length === 0) {
            wordsListElement.innerHTML = '<tr><td colspan="4" style="text-align: center; padding: 30px;">Словарь пуст. Начните добавлять слова!</td></tr>';
        } else {
            words.forEach(word => {
                const row = document.createElement('tr');
                row.innerHTML = `
                    <td>${word.word}</td>
                    <td>${getPartOfSpeechName(word.part_of_speech)}</td>
                    <td>${word.translation}</td>
                    <td class="actions">
                        <button class="delete-btn" data-id="${word.id}">
                            <i class="fas fa-trash"></i> Удалить
                        </button>
                    </td>
                `;
                wordsListElement.appendChild(row);
            });

            document.querySelectorAll('.delete-btn').forEach(btn => {
                btn.addEventListener('click', function() {
                    const wordId = this.getAttribute('data-id');
                    deleteWord(wordId);
                });
            });
        }
    } catch (error) {
        console.error('Ошибка загрузки слов:', error);
        showNotification('Ошибка загрузки слов из словаря', 'error');
    } finally {
        wordsLoading.style.display = 'none';
    }
}

// Загрузка статистики
async function loadStatistics() {
    if (!currentUserId) return;

    try {
        const response = await fetch(`/api/stats?user_id=${currentUserId}`);

        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }

        const stats = await response.json();
        document.getElementById('statsContent').innerHTML = `
            <div style="display: flex; justify-content: space-around; flex-wrap: wrap; gap: 20px; margin-top: 20px;">
                <div style="background: #e8f5e9; padding: 15px; border-radius: 10px; min-width: 120px;">
                    <div style="font-size: 2rem; color: #2e7d32; font-weight: bold;">${stats.total_words || 0}</div>
                    <div>Всего слов</div>
                </div>
                <div style="background: #e8f5e9; padding: 15px; border-radius: 10px; min-width: 120px;">
                    <div style="font-size: 2rem; color: #2e7d32; font-weight: bold;">${stats.nouns || 0}</div>
                    <div>Существительных</div>
                </div>
                <div style="background: #e8f5e9; padding: 15px; border-radius: 10px; min-width: 120px;">
                    <div style="font-size: 2rem; color: #2e7d32; font-weight: bold;">${stats.verbs || 0}</div>
                    <div>Глаголов</div>
                </div>
            </div>
        `;
    } catch (error) {
        console.error('Ошибка загрузки статистики:', error);
        document.getElementById('statsContent').innerHTML = 'Ошибка загрузки статистики';
    }
}

// Добавление нового слова
async function addWord() {
    const word = document.getElementById('newWord').value.trim().toLowerCase();
    const partOfSpeech = document.getElementById('partOfSpeech').value;
    const translation = document.getElementById('translation').value.trim();

    if (!word || !translation) {
        showNotification('Пожалуйста, заполните все поля', 'error');
        return;
    }

    if (!currentUserId) {
        showNotification('Ошибка: Не указан ID пользователя', 'error');
        return;
    }

    try {
        loadingOverlay.style.display = 'flex';

        const response = await fetch(`/api/words`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({
                user_id: currentUserId,
                word: word,
                part_of_speech: partOfSpeech,
                translation: translation
            })
        });

        if (!response.ok) {
            const errorData = await response.json();
            throw new Error(errorData.error || 'Ошибка сервера');
        }

        document.getElementById('newWord').value = '';
        document.getElementById('translation').value = '';
        showNotification(`Слово "${word}" добавлено в словарь!`, 'success');

        if (document.getElementById('all-words').classList.contains('active')) {
            loadWords();
        }
        if (document.getElementById('statistics').classList.contains('active')) {
            loadStatistics();
        }
    } catch (error) {
        console.error('Ошибка добавления слова:', error);
        showNotification(`Ошибка: ${error.message}`, 'error');
    } finally {
        loadingOverlay.style.display = 'none';
    }
}

// Поиск перевода
async function findTranslation() {
    const word = document.getElementById('searchWord').value.trim().toLowerCase();
    if (!word) {
        showNotification('Введите слово для поиска', 'error');
        return;
    }

    if (!currentUserId) {
        showNotification('Ошибка: Не указан ID пользователя', 'error');
        return;
    }

    try {
        loadingOverlay.style.display = 'flex';
        const response = await fetch(`/api/words/search?user_id=${currentUserId}&word=${encodeURIComponent(word)}`);

        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }

        const result = await response.json();

        if (result && result.word) {
            document.getElementById('resultWord').textContent = result.word;
            document.getElementById('resultPos').textContent = getPartOfSpeechName(result.part_of_speech);
            document.getElementById('resultTranslation').textContent = result.translation;
            document.getElementById('searchResult').style.display = 'block';
        } else {
            document.getElementById('resultWord').textContent = word;
            document.getElementById('resultPos').textContent = 'не найдено';
            document.getElementById('resultTranslation').textContent = 'Слово не найдено в словаре';
            document.getElementById('searchResult').style.display = 'block';
        }
    } catch (error) {
        console.error('Ошибка поиска слова:', error);
        showNotification('Ошибка при поиске слова', 'error');
    } finally {
        loadingOverlay.style.display = 'none';
    }
}

// Удаление слова
async function deleteWord(wordId) {
    if (!confirm('Вы уверены, что хотите удалить это слово?')) return;

    if (!currentUserId) {
        showNotification('Ошибка: Не указан ID пользователя', 'error');
        return;
    }

    try {
        loadingOverlay.style.display = 'flex';
        const response = await fetch(`/api/words/${wordId}?user_id=${currentUserId}`, {
            method: 'DELETE'
        });

        if (!response.ok) {
            throw new Error(`Ошибка HTTP: ${response.status}`);
        }

        showNotification('Слово успешно удалено', 'success');
        loadWords();
        if (document.getElementById('statistics').classList.contains('active')) {
            loadStatistics();
        }
    } catch (error) {
        console.error('Ошибка удаления слова:', error);
        showNotification('Ошибка при удалении слова', 'error');
    } finally {
        loadingOverlay.style.display = 'none';
    }
}

// Вспомогательные функции
function getPartOfSpeechName(code) {
    const names = {
        'noun': 'Существительное',
        'verb': 'Глагол',
        'adjective': 'Прилагательное',
        'adverb': 'Наречие',
        'other': 'Другое'
    };
    return names[code] || code;
}

function showNotification(message, type) {
    notificationElement.textContent = message;
    notificationElement.className = `notification ${type} show`;
    setTimeout(() => {
        notificationElement.classList.remove('show');
    }, 3000);
}