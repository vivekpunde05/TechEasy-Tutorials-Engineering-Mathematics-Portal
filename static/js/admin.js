/**
 * TechEasy Tutorials - Engineering Mathematics
 * Admin Panel Client JavaScript (Dynamic Dropdowns, Math Symbols Toolbar, Live MathJax Preview)
 */

document.addEventListener('DOMContentLoaded', () => {
    // 1. Dynamic Subject -> Chapter Dropdown
    const subjectSelect = document.getElementById('subject_select');
    const chapterSelect = document.getElementById('chapter_select');

    if (subjectSelect && chapterSelect) {
        subjectSelect.addEventListener('change', async function() {
            const subjectId = this.value;
            chapterSelect.innerHTML = '<option value="">Loading chapters...</option>';
            chapterSelect.disabled = true;

            if (!subjectId) {
                chapterSelect.innerHTML = '<option value="">-- First Select Subject --</option>';
                chapterSelect.disabled = false;
                return;
            }

            try {
                const res = await fetch(`/api/chapters?subject_id=${subjectId}`);
                const chapters = await res.json();

                if (chapters.length === 0) {
                    chapterSelect.innerHTML = '<option value="">No chapters found for this subject</option>';
                } else {
                    let html = '<option value="">-- Select Chapter --</option>';
                    chapters.forEach(ch => {
                        html += `<option value="${ch.id}">${ch.chapter_name}</option>`;
                    });
                    chapterSelect.innerHTML = html;
                }
            } catch (err) {
                chapterSelect.innerHTML = '<option value="">Error loading chapters</option>';
                console.error(err);
            } finally {
                chapterSelect.disabled = false;
            }
        });
    }

    // 2. Math Symbols Helper Toolbar
    const mathToolbar = document.getElementById('mathToolbar');
    const questionInput = document.getElementById('question');
    const explanationInput = document.getElementById('explanation');
    let activeTextarea = questionInput;

    if (questionInput) {
        questionInput.addEventListener('focus', () => { activeTextarea = questionInput; });
    }
    if (explanationInput) {
        explanationInput.addEventListener('focus', () => { activeTextarea = explanationInput; });
    }

    if (mathToolbar) {
        mathToolbar.querySelectorAll('.math-sym-btn').forEach(btn => {
            btn.addEventListener('click', (e) => {
                e.preventDefault();
                const snippet = btn.dataset.snippet || btn.textContent;
                insertSnippet(snippet);
            });
        });
    }

    function insertSnippet(snippet) {
        if (!activeTextarea) return;
        const start = activeTextarea.selectionStart;
        const end = activeTextarea.selectionEnd;
        const text = activeTextarea.value;
        activeTextarea.value = text.substring(0, start) + snippet + text.substring(end);
        activeTextarea.selectionStart = activeTextarea.selectionEnd = start + snippet.length;
        activeTextarea.focus();
        triggerLivePreview();
    }

    // 3. Live MathJax Preview
    const previewContainer = document.getElementById('liveMathPreview');
    const previewInputs = [
        questionInput,
        document.getElementById('option_a'),
        document.getElementById('option_b'),
        document.getElementById('option_c'),
        document.getElementById('option_d'),
        explanationInput
    ].filter(Boolean);

    let previewDebounce = null;
    function triggerLivePreview() {
        if (!previewContainer) return;
        clearTimeout(previewDebounce);
        previewDebounce = setTimeout(() => {
            const q = questionInput ? questionInput.value : '';
            const oa = document.getElementById('option_a') ? document.getElementById('option_a').value : '';
            const ob = document.getElementById('option_b') ? document.getElementById('option_b').value : '';
            const oc = document.getElementById('option_c') ? document.getElementById('option_c').value : '';
            const od = document.getElementById('option_d') ? document.getElementById('option_d').value : '';
            const exp = explanationInput ? explanationInput.value : '';

            previewContainer.innerHTML = `
                <div style="font-weight:700; margin-bottom:10px; font-size:1.1rem;">Live Preview:</div>
                <div style="font-size:1.05rem; margin-bottom:14px;"><strong>Q:</strong> ${q || '<em style="color:#94a3b8">Enter question text...</em>'}</div>
                <div style="display:grid; grid-template-columns:1fr 1fr; gap:10px; margin-bottom:14px; font-size:0.95rem;">
                    <div><strong>(A)</strong> ${oa}</div>
                    <div><strong>(B)</strong> ${ob}</div>
                    <div><strong>(C)</strong> ${oc}</div>
                    <div><strong>(D)</strong> ${od}</div>
                </div>
                ${exp ? `<div style="padding:10px; background:var(--bg-surface); border-radius:8px; font-size:0.9rem;"><strong>Explanation:</strong> ${exp}</div>` : ''}
            `;

            if (window.renderMath) window.renderMath();
        }, 300);
    }

    previewInputs.forEach(input => {
        input.addEventListener('input', triggerLivePreview);
    });

    if (previewContainer && questionInput && questionInput.value) {
        triggerLivePreview();
    }
});
