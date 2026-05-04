// CTF Platform - Интерактивные возможности

document.addEventListener('DOMContentLoaded', function() {
    // Инициализация инструментов
    initTools();

    // Анимации при скролле
    initScrollAnimations();

    // Интерактивные элементы
    initInteractiveElements();

    // Таймеры и обновления
    initTimers();
});

// Инициализация инструментов
function initTools() {
    // Копирование флагов
    document.querySelectorAll('.copy-flag-btn').forEach(button => {
        button.addEventListener('click', function() {
            const flag = this.dataset.flag;
            navigator.clipboard.writeText(flag).then(() => {
                const originalHTML = this.innerHTML;
                this.innerHTML = '<i class="bi bi-check"></i> Скопировано';
                this.classList.add('btn-success');

                setTimeout(() => {
                    this.innerHTML = originalHTML;
                    this.classList.remove('btn-success');
                }, 2000);
            });
        });
    });

    // Подсветка синтаксиса
    document.querySelectorAll('pre code').forEach((block) => {
        // Простая подсветка для демонстрации
        const html = block.innerHTML
            .replace(/&lt;!--.*?--&gt;/g, '<span class="comment">&lt;!--$&--&gt;</span>')
            .replace(/(&lt;\/?[a-zA-Z][^&]*?&gt;)/g, '<span class="tag">$1</span>')
            .replace(/(".*?")/g, '<span class="string">$1</span>')
            .replace(/\b(function|return|if|else|for|while|var|let|const)\b/g, '<span class="keyword">$1</span>');

        block.innerHTML = html;
    });
}

// Анимации при скролле
function initScrollAnimations() {
    const observer = new IntersectionObserver((entries) => {
        entries.forEach(entry => {
            if (entry.isIntersecting) {
                entry.target.classList.add('animate__animated', 'animate__fadeInUp');

                // Специальные анимации для статистики
                if (entry.target.classList.contains('stat-number')) {
                    animateCounter(entry.target);
                }
            }
        });
    }, {
        threshold: 0.1,
        rootMargin: '0px 0px -50px 0px'
    });

    // Наблюдаем за всеми элементами для анимации
    document.querySelectorAll('.animate-on-scroll').forEach(el => {
        observer.observe(el);
    });
}

// Анимация счетчиков
function animateCounter(element) {
    const target = parseInt(element.textContent);
    const duration = 2000; // 2 секунды
    const step = target / (duration / 16); // 60 FPS
    let current = 0;

    const timer = setInterval(() => {
        current += step;
        if (current >= target) {
            current = target;
            clearInterval(timer);
        }
        element.textContent = Math.floor(current);
    }, 16);
}

// Интерактивные элементы
function initInteractiveElements() {
    // Анимация кнопок
    document.querySelectorAll('.btn').forEach(button => {
        button.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-3px)';
        });

        button.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0)';
        });
    });

    // Анимация карточек
    document.querySelectorAll('.card').forEach(card => {
        card.addEventListener('mouseenter', function() {
            this.style.transform = 'translateY(-10px) scale(1.02)';
        });

        card.addEventListener('mouseleave', function() {
            this.style.transform = 'translateY(0) scale(1)';
        });
    });

    // Интерактивные категории
    document.querySelectorAll('.category-item').forEach(item => {
        item.addEventListener('mouseenter', function() {
            const icon = this.querySelector('.category-icon i');
            if (icon) {
                icon.style.transform = 'scale(1.2) rotate(10deg)';
            }
        });

        item.addEventListener('mouseleave', function() {
            const icon = this.querySelector('.category-icon i');
            if (icon) {
                icon.style.transform = 'scale(1) rotate(0)';
            }
        });
    });

    // Плавное раскрытие аккордеонов
    document.querySelectorAll('.accordion-button').forEach(button => {
        button.addEventListener('click', function() {
            const target = document.querySelector(this.getAttribute('data-bs-target'));
            if (target) {
                target.style.transition = 'height 0.3s ease';
            }
        });
    });
}

// Таймеры и обновления
function initTimers() {
    // Обновление времени в реальном времени
    function updateLocalTimes() {
        document.querySelectorAll('.local-time').forEach(element => {
            const timestamp = element.dataset.timestamp;
            if (timestamp) {
                const date = new Date(timestamp * 1000);
                const now = new Date();
                const diff = Math.floor((now - date) / 1000);

                let text;
                if (diff < 60) {
                    text = 'только что';
                } else if (diff < 3600) {
                    text = Math.floor(diff / 60) + ' мин назад';
                } else if (diff < 86400) {
                    text = Math.floor(diff / 3600) + ' ч назад';
                } else {
                    text = date.toLocaleDateString('ru-RU');
                }

                element.textContent = text;
            }
        });
    }

    updateLocalTimes();
    setInterval(updateLocalTimes, 60000); // Каждую минуту

    // Прогресс бар анимация
    document.querySelectorAll('.progress').forEach(progress => {
        const bar = progress.querySelector('.progress-bar');
        if (bar) {
            const width = bar.style.width;
            bar.style.width = '0%';

            setTimeout(() => {
                bar.style.width = width;
                bar.style.transition = 'width 1.5s ease-in-out';
            }, 300);
        }
    });

    // Автоматическое скрытие уведомлений
    setTimeout(() => {
        document.querySelectorAll('.alert').forEach(alert => {
            const bsAlert = new bootstrap.Alert(alert);
            setTimeout(() => {
                bsAlert.close();
            }, 5000);
        });
    }, 100);
}

// Дополнительные утилиты
function showNotification(message, type = 'info') {
    const container = document.querySelector('.flashes') || document.body;
    const alert = document.createElement('div');
    alert.className = `alert alert-${type} alert-dismissible fade show`;
    alert.innerHTML = `
        <div class="d-flex align-items-center">
            <i class="bi bi-${getIconForType(type)} me-2"></i>
            <span>${message}</span>
        </div>
        <button type="button" class="btn-close btn-close-white" data-bs-dismiss="alert"></button>
    `;

    container.appendChild(alert);

    setTimeout(() => {
        const bsAlert = new bootstrap.Alert(alert);
        bsAlert.close();
    }, 5000);
}

function getIconForType(type) {
    const icons = {
        'success': 'check-circle',
        'danger': 'exclamation-triangle',
        'warning': 'exclamation-circle',
        'info': 'info-circle'
    };
    return icons[type] || 'info-circle';
}

// Экспорт для использования в консоли
window.CTFPlatform = {
    showNotification,
    animateCounter
};