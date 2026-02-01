import i18n from './i18n';

// V3.5.0: 使用 JSZip 批量打包下载
const t = i18n.t.bind(i18n);
const downloadSelectedHistory = async () => {
    const selectedIds = Array.from(historySelection);
    if (selectedIds.length === 0) return;

    // 如果只选了一个且是单图/单视频，直接下载文件（保持原有体验）
    const firstItem = history.find(h => h.id === selectedIds[0]);
    const isSingleSimpleItem = selectedIds.length === 1 && !firstItem?.mjImages && firstItem?.url;

    if (isSingleSimpleItem) {
        try {
            const url = firstItem.url;
            const ext = url.startsWith('data:image') ? 'png' : url.split('.').pop().split('?')[0] || 'png';
            const filename = `${firstItem.prompt?.slice(0, 20) || 'download'}.${ext}`;
            if (url.startsWith('data:')) {
                const a = document.createElement('a');
                a.href = url;
                a.download = filename;
                a.click();
            } else {
                const resp = await fetch(url);
                const blob = await resp.blob();
                const a = document.createElement('a');
                a.href = URL.createObjectURL(blob);
                a.download = filename;
                a.click();
            }
            toast.success(t('下载已开始'));
        } catch (e) {
            console.error('下载失败:', e);
            toast.error(t('下载失败'));
        }
        return;
    }

    const zip = new JSZip();
    let count = 0;
    const total = selectedIds.length;
    const toastId = toast.loading(`${t('正在打包')} ${total} ${t('个项目')}...`);

    try {
        for (const id of selectedIds) {
            const item = history.find(h => h.id === id);
            if (!item) continue;

            // 统一处理所有资源链接
            const resources = [];
            if (item.mjImages && item.mjImages.length > 0) {
                // Midjourney 4宫格
                item.mjImages.forEach((url, idx) => {
                    resources.push({ url, suffix: `_${idx + 1}` });
                });
            } else if (item.url) {
                // 普通单图/视频
                resources.push({ url: item.url, suffix: '' });
            }

            for (const res of resources) {
                try {
                    let blob;
                    if (res.url.startsWith('data:')) {
                        // Data URL 转 Blob
                        const arr = res.url.split(',');
                        const mime = arr[0].match(/:(.*?);/)[1];
                        const bstr = atob(arr[1]);
                        let n = bstr.length;
                        const u8arr = new Uint8Array(n);
                        while (n--) u8arr[n] = bstr.charCodeAt(n);
                        blob = new Blob([u8arr], { type: mime });
                    } else {
                        // 网络 URL 下载
                        const resp = await fetch(res.url);
                        blob = await resp.blob();
                    }

                    // 生成文件名
                    let ext = blob.type.split('/')[1] || 'png';
                    if (item.url && !item.url.startsWith('data:')) {
                        const urlExt = item.url.split('.').pop().split('?')[0];
                        if (urlExt && urlExt.length < 5) ext = urlExt;
                    }

                    // 清理文件名非法字符
                    const promptSlug = (item.prompt || 'untitled').replace(/[\\/:*?"<>|]/g, '_').slice(0, 50);
                    const filename = `${promptSlug}${res.suffix}.${ext}`;

                    zip.file(filename, blob);
                    count++;
                } catch (err) {
                    console.error(`打包资源失败 [${id}]:`, err);
                }
            }
        }

        if (count === 0) {
            toast.error(t('没有可下载的有效资源'), { id: toastId });
            return;
        }

        // 生成 ZIP
        const content = await zip.generateAsync({ type: 'blob' });
        const now = new Date();
        const timestamp = `${now.getFullYear().toString().slice(2)}${(now.getMonth() + 1).toString().padStart(2, '0')}${now.getDate().toString().padStart(2, '0')}-${now.getHours().toString().padStart(2, '0')}${now.getMinutes().toString().padStart(2, '0')}`;
        saveAs(content, `tapnow-assets-${timestamp}.zip`);

        toast.success(`${t('打包完成，已下载')} ${count} ${t('个文件')}`, { id: toastId });
    } catch (e) {
        console.error('打包过程出错:', e);
        toast.error(t('打包失败，请查看控制台'), { id: toastId });
    }
};
