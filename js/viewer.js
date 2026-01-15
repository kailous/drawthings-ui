// viewer.js - 优化版手势引擎 (Smooth & Elastic)
class ImageViewer {
    constructor(options = {}) {
        this.els = options.elements;
        this.data = [];
        this.currentIndex = -1;
        
        // 配置参数
        this.config = {
            doubleTapDelay: 300,
            maxScale: 3,
            swipeThreshold: 60,     // 左右切图触发距离
            closeThreshold: 100,    // 下滑关闭触发距离
            resistance: 0.4,        // 未放大时的拖拽阻尼 (越小越难拖)
            ...options.config
        };

        // 状态机
        this.state = {
            isOpen: false,
            scale: 1,
            // 当前渲染的偏移量
            currX: 0, currY: 0,
            // 拖拽起始时的偏移量
            baseX: 0, baseY: 0,
            // 手指起始坐标
            startX: 0, startY: 0,
            isDragging: false,
            lastTapTime: 0
        };

        // 绑定上下文
        this.onPointerDown = this.onPointerDown.bind(this);
        this.onPointerMove = this.onPointerMove.bind(this);
        this.onPointerUp = this.onPointerUp.bind(this);
        this.onKeyDown = this.onKeyDown.bind(this);
        
        this.initEvents();
    }

    initEvents() {
        const { img, close, prev, next, modal } = this.els;
        
        // 核心手势：绑定在图片上
        img.addEventListener('pointerdown', this.onPointerDown);
        // pointermove 和 pointerup 绑定在 document 上，防止拖出图片范围丢失焦点
        document.addEventListener('pointermove', this.onPointerMove);
        document.addEventListener('pointerup', this.onPointerUp);
        document.addEventListener('pointercancel', this.onPointerUp);
        
        img.addEventListener('dragstart', e => e.preventDefault()); // 禁原生拖拽

        // UI 交互
        close.onclick = () => this.close();
        prev.onclick = (e) => { e.stopPropagation(); this.navigate(-1); };
        next.onclick = (e) => { e.stopPropagation(); this.navigate(1); };
        modal.onclick = (e) => { if (e.target === modal) this.close(); };
        document.addEventListener('keydown', this.onKeyDown);
    }

    open(items, index = 0) {
        this.data = items;
        this.currentIndex = index;
        this.state.isOpen = true;
        this.els.modal.classList.add('open');
        this.resetState();
        this.loadImage(this.currentIndex);
    }

    close() {
        if (!this.state.isOpen) return;
        this.state.isOpen = false;
        this.els.modal.classList.remove('open');
        this.els.modal.style.backgroundColor = ''; 
        setTimeout(() => this.els.img.src = '', 300);
    }

    // 优化：带预加载的切图，解决闪烁问题
    navigate(dir) {
        const nextIdx = this.currentIndex + dir;
        if (nextIdx < 0 || nextIdx >= this.data.length) {
            this.animateBounce(); // 到底回弹
            return;
        }

        // 1. 先淡出旧图
        this.els.img.style.transition = 'opacity 0.15s ease';
        this.els.img.style.opacity = '0.4';

        // 2. 预加载新图 (Image 对象)
        const nextItem = this.data[nextIdx];
        const nextUrl = typeof nextItem === 'string' ? nextItem : nextItem.url;
        const tempImg = new Image();
        
        tempImg.onload = () => {
            // 3. 加载完成后再切换
            this.currentIndex = nextIdx;
            this.els.img.src = nextUrl;
            this.updateNavButtons();
            this.resetState();
            
            // 4. 淡入
            requestAnimationFrame(() => {
                 this.els.img.style.opacity = '1';
            });
        };
        tempImg.src = nextUrl;
    }

    // 真正的图片加载器
    loadImage(index) {
        const item = this.data[index];
        const url = typeof item === 'string' ? item : item.url;
        this.els.img.src = url;
        this.els.img.style.opacity = '1';
        this.updateNavButtons();
    }

    updateNavButtons() {
        const { prev, next } = this.els;
        if (!prev || !next) return;
        if (this.currentIndex === -1 || this.data.length <= 1) {
            prev.style.display = 'none'; next.style.display = 'none'; return;
        }
        prev.style.display = 'block'; next.style.display = 'block';
        prev.style.opacity = this.currentIndex > 0 ? 1 : 0.3;
        next.style.opacity = this.currentIndex < this.data.length - 1 ? 1 : 0.3;
    }

    // --- 手势核心 ---

    onPointerDown(e) {
        if (!this.state.isOpen) return;
        e.preventDefault();

        // 双击检测
        const now = Date.now();
        if (now - this.state.lastTapTime < this.config.doubleTapDelay) {
            this.toggleZoom(e.clientX, e.clientY);
            this.state.lastTapTime = 0;
            return;
        }
        this.state.lastTapTime = now;

        // 启动拖拽
        this.state.isDragging = true;
        this.state.startX = e.clientX;
        this.state.startY = e.clientY;
        
        // 记录按下时的基础位置
        this.state.baseX = this.state.currX;
        this.state.baseY = this.state.currY;

        // 移除过渡动画，保证拖拽跟手
        this.els.img.style.transition = 'none';
        // 捕获指针
        this.els.img.setPointerCapture(e.pointerId);
    }

    onPointerMove(e) {
        if (!this.state.isDragging) return;
        e.preventDefault();

        // 算出手指移动距离
        const deltaX = e.clientX - this.state.startX;
        const deltaY = e.clientY - this.state.startY;

        if (this.state.scale > 1) {
            // --- 放大模式：绝对跟手 ---
            // 也就是：当前位置 = 拖拽前的位置 + 手指移动量
            this.state.currX = this.state.baseX + deltaX;
            this.state.currY = this.state.baseY + deltaY;
            this.requestRender();
        } else {
            // --- 未放大模式：带阻尼的拉动 (Rubber Banding) ---
            // 解决问题 3：乘系数让它“拖不动”
            this.state.currX = deltaX * this.config.resistance;
            this.state.currY = deltaY * this.config.resistance;

            // 解决问题 4：下滑检测 (只看 Y 轴)
            if (deltaY > 0) {
                // 根据下拉距离计算背景透明度
                const opacity = Math.max(0, 1 - deltaY / 300);
                this.els.modal.style.backgroundColor = `rgba(0, 0, 0, ${0.95 * opacity})`;
            }
            this.requestRender();
        }
    }

    onPointerUp(e) {
        if (!this.state.isDragging) return;
        this.state.isDragging = false;
        
        // 恢复过渡动画 (为了回弹效果)
        this.els.img.style.transition = 'transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)';

        if (this.state.scale > 1) {
            // 放大模式松手：不做特殊处理，保留在当前位置 (或者加边界检查)
        } else {
            // 未放大模式松手：判定意图
            const deltaX = this.state.currX / this.config.resistance; // 还原真实移动距离
            const deltaY = this.state.currY / this.config.resistance;

            // 1. 下滑关闭
            if (deltaY > this.config.closeThreshold) {
                this.close();
                return;
            }

            // 2. 左右切图
            if (Math.abs(deltaX) > this.config.swipeThreshold) {
                if (deltaX > 0) this.navigate(-1);
                else this.navigate(1);
            } else {
                // 3. 没达到阈值：回弹归位 (Snap Back)
                this.resetState();
                this.els.modal.style.backgroundColor = ''; // 恢复背景
            }
        }
    }

    toggleZoom(x, y) {
        if (this.state.scale > 1) {
            // 缩小归位
            this.resetState();
        } else {
            // 放大
            this.state.scale = this.config.maxScale;
            // 简单处理：重置偏移，居中放大 (复杂的定点放大需要计算 transform-origin)
            this.state.currX = 0;
            this.state.currY = 0;
            this.requestRender();
        }
        this.els.img.style.transition = 'transform 0.3s cubic-bezier(0.25, 0.8, 0.25, 1)';
    }

    // 状态重置 (回弹)
    resetState() {
        this.state.scale = 1;
        this.state.currX = 0;
        this.state.currY = 0;
        this.requestRender();
    }

    // 边界回弹动画
    animateBounce() {
        const keyframes = [
            { transform: 'translateX(0)' },
            { transform: 'translateX(-15px)' },
            { transform: 'translateX(15px)' },
            { transform: 'translateX(0)' }
        ];
        this.els.img.animate(keyframes, { duration: 300, easing: 'ease-out' });
        this.resetState();
    }

    // 使用 rAF 进行渲染，避免掉帧
    requestRender() {
        requestAnimationFrame(() => {
            const { currX, currY, scale } = this.state;
            this.els.img.style.transform = `translate3d(${currX}px, ${currY}px, 0) scale(${scale})`;
        });
    }

    onKeyDown(e) {
        if (!this.state.isOpen) return;
        if (e.key === 'Escape') this.close();
        if (e.key === 'ArrowLeft') this.navigate(-1);
        if (e.key === 'ArrowRight') this.navigate(1);
    }
}