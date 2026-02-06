// Edge浏览器兼容性修复

(function() {
    'use strict';
    
    // 1. 检查浏览器
    const isEdge = /Edge/.test(navigator.userAgent);
    const isIE = /Trident/.test(navigator.userAgent);
    
    if (isEdge || isIE) {
        // 2. 应用Edge专用修复
        applyEdgeFixes();
    }
    
    function applyEdgeFixes() {
        // 修复Flexbox布局
        fixFlexbox();
        
        // 修复表格布局
        fixTables();
        
        // 修复模态框
        fixModals();
        
        // 修复按钮点击效果
        fixButtons();
        
        // 优化图片加载
        optimizeImages();
    }
    
    function fixFlexbox() {
        // 为所有Flex容器添加min-height
        document.querySelectorAll('.row, .d-flex, .action-buttons').forEach(el => {
            if (!el.style.minHeight) {
                el.style.minHeight = '0.01px';
            }
        });
    }
    
    function fixTables() {
        // 为表格添加固定布局
        document.querySelectorAll('table').forEach(table => {
            table.style.tableLayout = 'fixed';
        });
    }
    
    function fixModals() {
        // 修复模态框在Edge中的显示问题
        const modals = document.querySelectorAll('.modal');
        modals.forEach(modal => {
            modal.style.display = 'none';
            modal.style.overflow = 'auto';
        });
    }
    
    function fixButtons() {
        // 防止按钮在Edge中双击
        let lastClickTime = 0;
        document.querySelectorAll('.btn').forEach(btn => {
            btn.addEventListener('click', function(e) {
                const now = Date.now();
                if (now - lastClickTime < 300) {
                    e.preventDefault();
                    e.stopPropagation();
                }
                lastClickTime = now;
            }, true);
        });
    }
    
    function optimizeImages() {
        // 延迟加载图片优化
        const images = document.querySelectorAll('img');
        images.forEach(img => {
            if (!img.loading) {
                img.loading = 'lazy';
            }
        });
    }
    
    // DOM加载完成后执行
    if (document.readyState === 'loading') {
        document.addEventListener('DOMContentLoaded', applyEdgeFixes);
    } else {
        applyEdgeFixes();
    }
})();