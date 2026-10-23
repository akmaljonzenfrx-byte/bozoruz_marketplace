/**
 * BozorUz - Onlayn Savdo Platformasi Asosiy JavaScript
 */

// Helper: Pul miqdorini formatlash (masalan, 1250000 -> 1 250 000 so'm)
function formatMoney(amount) {
    const number = parseInt(amount) || 0;
    return number.toLocaleString('ru-RU').replace(/,/g, ' ') + " so'm";
}

// Helper: Toast Xabarnomalarni ko'rsatish
function renderNotification(text, type = 'info') {
    let container = document.getElementById('toast-container');
    if (!container) {
        container = document.createElement('div');
        container.id = 'toast-container';
        container.className = 'fixed bottom-5 right-5 z-50 flex flex-col gap-2 max-w-sm w-full px-4 pointer-events-none';
        document.body.appendChild(container);
    }

    const toast = document.createElement('div');
    toast.className = `toast-item pointer-events-auto transform transition-all duration-300 translate-y-5 opacity-0 flex items-center gap-3 p-4 rounded-xl shadow-lg border text-sm font-medium ${getToastStyle(type)}`;
    
    const icon = getToastIcon(type);
    toast.innerHTML = `
        <span class="text-xl flex-shrink-0">${icon}</span>
        <div class="flex-grow">${text}</div>
        <button onclick="this.parentElement.remove()" class="text-gray-400 hover:text-gray-600 dark:hover:text-gray-200">
            <svg class="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24"><path stroke-linecap="round" stroke-linejoin="round" stroke-width="2" d="6 18L18 6M6 6l12 12"/></svg>
        </button>
    `;

    container.appendChild(toast);

    requestAnimationFrame(() => {
        toast.classList.remove('translate-y-5', 'opacity-0');
        toast.classList.add('translate-y-0', 'opacity-100');
    });

    setTimeout(() => {
        toast.classList.remove('translate-y-0', 'opacity-100');
        toast.classList.add('translate-y-5', 'opacity-0');
        setTimeout(() => toast.remove(), 300);
    }, 4000);
}

function getToastStyle(type) {
    switch(type) {
        case 'success':
            return 'bg-emerald-50 dark:bg-emerald-950 border-emerald-200 dark:border-emerald-800 text-emerald-800 dark:text-emerald-200';
        case 'error':
        case 'danger':
            return 'bg-rose-50 dark:bg-rose-950 border-rose-200 dark:border-rose-800 text-rose-800 dark:text-rose-200';
        case 'warning':
            return 'bg-amber-50 dark:bg-amber-950 border-amber-200 dark:border-amber-800 text-amber-800 dark:text-amber-200';
        default:
            return 'bg-indigo-50 dark:bg-indigo-950 border-indigo-200 dark:border-indigo-800 text-indigo-800 dark:text-indigo-200';
    }
}

function getToastIcon(type) {
    switch(type) {
        case 'success': return '✅';
        case 'error':
        case 'danger': return '❌';
        case 'warning': return '⚠️';
        default: return 'ℹ️';
    }
}

// 1. Theme Toggle (Yorug' / Qorong'u tema)
function toggleTheme() {
    const isDark = document.documentElement.classList.toggle('dark');
    localStorage.setItem('bozoruz_theme', isDark ? 'dark' : 'light');
    
    const themeIcon = document.getElementById('theme-toggle-icon');
    if (themeIcon) {
        themeIcon.textContent = isDark ? '☀️' : '🌙';
    }
    renderNotification(isDark ? "Qorong'u rejim yoqildi" : "Yorug' rejim yoqildi", "info");
}

function initTheme() {
    const savedTheme = localStorage.getItem('bozoruz_theme');
    if (savedTheme === 'dark' || (!savedTheme && window.matchMedia('(prefers-color-scheme: dark)').matches)) {
        document.documentElement.classList.add('dark');
        const themeIcon = document.getElementById('theme-toggle-icon');
        if (themeIcon) themeIcon.textContent = '☀️';
    } else {
        document.documentElement.classList.remove('dark');
        const themeIcon = document.getElementById('theme-toggle-icon');
        if (themeIcon) themeIcon.textContent = '🌙';
    }
}

// 2. Dynamic Live Search with Suggestions
function setupLiveSearch() {
    const searchInputs = document.querySelectorAll('.live-search-input');
    
    searchInputs.forEach(input => {
        const wrapper = input.closest('.search-wrapper') || input.parentElement;
        let suggestionBox = wrapper.querySelector('.search-suggestions');

        if (!suggestionBox) {
            suggestionBox = document.createElement('div');
            suggestionBox.className = 'search-suggestions hidden absolute left-0 right-0 top-full mt-2 bg-white dark:bg-gray-800 rounded-2xl shadow-2xl border border-gray-100 dark:border-gray-700 z-50 overflow-hidden max-h-96 overflow-y-auto';
            wrapper.appendChild(suggestionBox);
        }

        let debounceTimer;

        input.addEventListener('input', (e) => {
            clearTimeout(debounceTimer);
            const query = e.target.value.trim();

            if (query.length < 2) {
                suggestionBox.classList.add('hidden');
                suggestionBox.innerHTML = '';
                return;
            }

            debounceTimer = setTimeout(() => {
                fetch(`/api/search-suggestions?q=${encodeURIComponent(query)}`)
                    .then(res => res.json())
                    .then(data => {
                        if (data.results && data.results.length > 0) {
                            let html = '<div class="p-2 text-xs font-semibold uppercase tracking-wider text-gray-400 dark:text-gray-500 border-b dark:border-gray-700">Tavsiyalar</div>';
                            data.results.forEach(item => {
                                html += `
                                    <a href="/product/${item.id}" class="flex items-center gap-3 p-3 hover:bg-indigo-50 dark:hover:bg-gray-700/50 transition-colors">
                                        <div class="w-10 h-10 rounded-xl bg-gradient-to-br ${item.color_theme || 'from-indigo-500 to-purple-600'} flex items-center justify-center text-xl text-white flex-shrink-0 shadow-sm">
                                            ${item.icon || '📦'}
                                        </div>
                                        <div class="flex-grow min-w-0">
                                            <div class="text-sm font-medium text-gray-800 dark:text-gray-100 truncate">${highlightQuery(item.name, query)}</div>
                                            <div class="text-xs text-indigo-600 dark:text-indigo-400 font-semibold">${formatMoney(item.price)}</div>
                                        </div>
                                        <span class="text-xs text-gray-400 font-normal truncate max-w-[80px]">${item.category_name || ''}</span>
                                    </a>
                                `;
                            });
                            suggestionBox.innerHTML = html;
                            suggestionBox.classList.remove('hidden');
                        } else {
                            suggestionBox.innerHTML = `
                                <div class="p-4 text-center text-sm text-gray-500 dark:text-gray-400">
                                    "<strong>${query}</strong>" bo'yicha hech narsa topilmadi
                                </div>
                            `;
                            suggestionBox.classList.remove('hidden');
                        }
                    })
                    .catch(() => {
                        suggestionBox.classList.add('hidden');
                    });
            }, 250);
        });

        document.addEventListener('click', (e) => {
            if (!wrapper.contains(e.target)) {
                suggestionBox.classList.add('hidden');
            }
        });
    });
}

function highlightQuery(text, query) {
    const regex = new RegExp(`(${query})`, 'gi');
    return text.replace(regex, '<mark class="bg-amber-200 dark:bg-amber-800/60 dark:text-amber-100 text-gray-900 rounded px-0.5">$1</mark>');
}

// 3. Cart AJAX Actions
function addToCart(productId, quantity = 1, variant = null) {
    const payload = {
        product_id: parseInt(productId),
        quantity: parseInt(quantity),
        variant: variant
    };

    fetch('/api/cart/add', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(payload)
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            updateCartBadge(data.cart_count);
            renderNotification(data.message || "Mahsulot savatga qo'shildi!", "success");
            
            // Tugma ustida animatsiya ko'rsatish
            const btn = document.querySelector(`[data-cart-btn="${productId}"]`);
            if (btn) {
                const origText = btn.innerHTML;
                btn.innerHTML = '✓ Savatda';
                btn.classList.add('bg-emerald-600', 'text-white');
                setTimeout(() => {
                    btn.innerHTML = origText;
                    btn.classList.remove('bg-emerald-600', 'text-white');
                }, 2000);
            }
        } else {
            renderNotification(data.message || "Xatolik yuz berdi.", "danger");
        }
    })
    .catch(() => {
        renderNotification("Tarmoq xatosi. Qaytadan urinib ko'ring.", "danger");
    });
}

function updateCartQuantity(productId, quantity, variant = null) {
    fetch('/api/cart/update', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
            product_id: parseInt(productId),
            quantity: parseInt(quantity),
            variant: variant
        })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            updateCartBadge(data.cart_count);
            if (typeof window.reloadCartSummary === 'function') {
                window.reloadCartSummary(data);
            } else {
                window.location.reload();
            }
        } else {
            renderNotification(data.message || "Xatolik yuz berdi", "danger");
        }
    });
}

function updateCartBadge(count) {
    const badges = document.querySelectorAll('.cart-count-badge');
    badges.forEach(b => {
        b.textContent = count;
        if (count > 0) {
            b.classList.remove('hidden');
        } else {
            b.classList.add('hidden');
        }
    });
}

// 4. Wishlist Toggle AJAX
function addToWishlist(productId) {
    fetch('/api/wishlist/toggle', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: parseInt(productId) })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            renderNotification(data.message, data.is_in_wishlist ? "success" : "info");
            updateWishlistBadge(data.wishlist_count);

            const heartIcons = document.querySelectorAll(`.wishlist-btn-${productId}`);
            heartIcons.forEach(btn => {
                const icon = btn.querySelector('svg') || btn;
                if (data.is_in_wishlist) {
                    btn.classList.add('text-rose-500', 'fill-current');
                    btn.classList.remove('text-gray-400');
                } else {
                    btn.classList.remove('text-rose-500', 'fill-current');
                    btn.classList.add('text-gray-400');
                }
            });
        }
    })
    .catch(() => {
        renderNotification("Sevimli ro'yxatini yangilab bo'lmadi.", "danger");
    });
}

function updateWishlistBadge(count) {
    const badges = document.querySelectorAll('.wishlist-count-badge');
    badges.forEach(b => {
        b.textContent = count;
        if (count > 0) {
            b.classList.remove('hidden');
        } else {
            b.classList.add('hidden');
        }
    });
}

// 5. Installment Calculator
function calculateInstallment(price, months) {
    price = parseFloat(price) || 0;
    months = parseInt(months) || 12;

    // Uzum uslubida kichik ustama ko'effitsiyenti (3 oy - 0%, 6 oy - 5%, 12 oy - 12%)
    let coefficient = 1.0;
    if (months === 6) coefficient = 1.05;
    if (months === 12) coefficient = 1.12;

    const totalPrice = price * coefficient;
    const monthlyPayment = Math.round(totalPrice / months);

    return {
        months: months,
        totalPrice: totalPrice,
        monthlyPayment: monthlyPayment,
        formattedMonthly: formatMoney(monthlyPayment),
        formattedTotal: formatMoney(totalPrice)
    };
}

function updateInstallmentUI(price) {
    const monthSelectors = document.querySelectorAll('.installment-month-btn');
    const monthlyDisplay = document.getElementById('installment-monthly-price');
    const totalDisplay = document.getElementById('installment-total-price');

    if (!monthlyDisplay) return;

    monthSelectors.forEach(btn => {
        btn.addEventListener('click', function() {
            monthSelectors.forEach(b => b.classList.remove('border-indigo-600', 'bg-indigo-50', 'text-indigo-600', 'dark:bg-indigo-950/50', 'dark:text-indigo-400'));
            this.classList.add('border-indigo-600', 'bg-indigo-50', 'text-indigo-600', 'dark:bg-indigo-950/50', 'dark:text-indigo-400');

            const months = parseInt(this.dataset.months) || 12;
            const res = calculateInstallment(price, months);

            monthlyDisplay.textContent = res.formattedMonthly;
            if (totalDisplay) totalDisplay.textContent = res.formattedTotal;
        });
    });

    // Boshlang'ich default 12 oy
    const defaultBtn = document.querySelector('.installment-month-btn[data-months="12"]');
    if (defaultBtn) defaultBtn.click();
}

// 6. Countdown Timer for Sales / Flash Sale
function startCountdownTimer(deadlineString) {
    const timerElements = {
        hours: document.querySelectorAll('.timer-hours'),
        minutes: document.querySelectorAll('.timer-minutes'),
        seconds: document.querySelectorAll('.timer-seconds')
    };

    if (!timerElements.hours.length && !timerElements.minutes.length) return;

    let targetDate;
    if (deadlineString) {
        targetDate = new Date(deadlineString).getTime();
    } else {
        // Bugungi kungi yarim tun (00:00:00) gacha taymer
        targetDate = new Date().setHours(23, 59, 59, 999);
    }

    function update() {
        const now = new Date().getTime();
        const distance = targetDate - now;

        if (distance < 0) {
            targetDate = new Date().setHours(23, 59, 59, 999);
            return;
        }

        const hours = Math.floor((distance % (1000 * 60 * 60 * 24)) / (1000 * 60 * 60));
        const minutes = Math.floor((distance % (1000 * 60 * 60)) / (1000 * 60));
        const seconds = Math.floor((distance % (1000 * 60)) / 1000);

        const pad = (num) => String(num).padStart(2, '0');

        timerElements.hours.forEach(e => e.textContent = pad(hours));
        timerElements.minutes.forEach(e => e.textContent = pad(minutes));
        timerElements.seconds.forEach(e => e.textContent = pad(seconds));
    }

    update();
    setInterval(update, 1000);
}

// 7. Product Comparison System
function addToCompare(productId) {
    let compareList = JSON.parse(localStorage.getItem('bozoruz_compare') || '[]');
    productId = parseInt(productId);

    if (compareList.includes(productId)) {
        compareList = compareList.filter(id => id !== productId);
        renderNotification("Mahsulot solishtirishdan olib tashlandi", "info");
    } else {
        if (compareList.length >= 4) {
            renderNotification("Solishtirish uchun maksimal 4 ta mahsulot tanlashingiz mumkin.", "warning");
            return;
        }
        compareList.push(productId);
        renderNotification("Mahsulot solishtirish ro'yxatiga qo'shildi!", "success");
    }

    localStorage.setItem('bozoruz_compare', JSON.stringify(compareList));
    updateCompareBadge(compareList.length);
}

function updateCompareBadge(count) {
    const badges = document.querySelectorAll('.compare-count-badge');
    badges.forEach(b => {
        b.textContent = count;
        if (count > 0) b.classList.remove('hidden');
        else b.classList.add('hidden');
    });
}

// 8. Price Alert Modal & Handler
function addPriceAlert(productId) {
    const targetPrice = prompt("Ushbu mahsulot narxi necha so'mga tushganda sizga xabar beraylik?");
    if (!targetPrice || isNaN(targetPrice)) return;

    fetch('/api/price-alert', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ product_id: parseInt(productId), target_price: parseInt(targetPrice) })
    })
    .then(res => res.json())
    .then(data => {
        if (data.success) {
            renderNotification("Narx tushishi haqidagi xabarnoma muvaffaqiyatli o'rnatildi!", "success");
        } else {
            renderNotification(data.message || "Xatolik yuz berdi", "danger");
        }
    });
}

// Initialization on DOM Content Loaded
document.addEventListener('DOMContentLoaded', () => {
    initTheme();
    setupLiveSearch();
    startCountdownTimer();

    // Theme Button Event
    const themeBtn = document.getElementById('theme-toggle-btn');
    if (themeBtn) {
        themeBtn.addEventListener('click', toggleTheme);
    }

    // Compare badge initial load
    const compareList = JSON.parse(localStorage.getItem('bozoruz_compare') || '[]');
    updateCompareBadge(compareList.length);

    // Auto-dismiss alert messages after 5 seconds
    const alerts = document.querySelectorAll('.flash-alert');
    alerts.forEach(alert => {
        setTimeout(() => {
            alert.style.transition = 'opacity 0.5s ease';
            alert.style.opacity = '0';
            setTimeout(() => alert.remove(), 500);
        }, 5000);
    });

    // Mobile menu toggle logic
    const menuBtn = document.getElementById('mobile-menu-btn');
    const mobileDrawer = document.getElementById('mobile-drawer');
    const drawerClose = document.getElementById('mobile-drawer-close');

    if (menuBtn && mobileDrawer) {
        menuBtn.addEventListener('click', () => {
            mobileDrawer.classList.remove('translate-x-full');
            document.body.classList.add('overflow-hidden');
        });
    }

    if (drawerClose && mobileDrawer) {
        drawerClose.addEventListener('click', () => {
            mobileDrawer.classList.add('translate-x-full');
            document.body.classList.remove('overflow-hidden');
        });
    }
});