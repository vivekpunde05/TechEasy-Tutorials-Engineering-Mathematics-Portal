/**
 * TechEasy Tutorials - Engineering Mathematics
 * Computer-Based Test (CBT) Interactive Runner Engine
 */

class TestRunner {
    constructor(config) {
        this.questions = config.questions || [];
        this.timeLimitMinutes = config.timeLimit || 30;
        this.testFormId = config.formId || 'testSubmissionForm';
        this.currentIndex = 0;
        this.answers = {}; // { question_id: 'A' | 'B' | 'C' | 'D' }
        this.markedForReview = {}; // { question_id: boolean }

        this.remainingSeconds = this.timeLimitMinutes * 60;
        this.timerInterval = null;

        this.initDOM();
        this.initTimer();
        this.renderQuestion(0);
        this.updatePalette();
    }

    initDOM() {
        // Elements
        this.qNumberEl = document.getElementById('cbtQuestionNumber');
        this.qBodyEl = document.getElementById('cbtQuestionBody');
        this.qImageEl = document.getElementById('cbtQuestionImage');
        this.optionsContainer = document.getElementById('cbtOptionsContainer');
        this.prevBtn = document.getElementById('cbtPrevBtn');
        this.nextBtn = document.getElementById('cbtNextBtn');
        this.clearBtn = document.getElementById('cbtClearBtn');
        this.reviewBtn = document.getElementById('cbtReviewBtn');
        this.timerDisplay = document.getElementById('cbtTimerDisplay');
        this.paletteGrid = document.getElementById('cbtPaletteGrid');
        this.submitModal = document.getElementById('cbtSubmitModal');
        this.confirmSubmitBtn = document.getElementById('cbtConfirmSubmitBtn');
        this.openSubmitModalBtn = document.getElementById('cbtOpenSubmitModalBtn');
        this.cancelSubmitBtn = document.getElementById('cbtCancelSubmitBtn');
        this.testForm = document.getElementById(this.testFormId);

        // Bind Controls
        if (this.prevBtn) this.prevBtn.addEventListener('click', () => this.navigate(-1));
        if (this.nextBtn) this.nextBtn.addEventListener('click', () => this.navigate(1));
        if (this.clearBtn) this.clearBtn.addEventListener('click', () => this.clearAnswer());
        if (this.reviewBtn) this.reviewBtn.addEventListener('click', () => this.toggleReview());

        if (this.openSubmitModalBtn) {
            this.openSubmitModalBtn.addEventListener('click', () => this.showSubmitModal());
        }
        if (this.cancelSubmitBtn) {
            this.cancelSubmitBtn.addEventListener('click', () => this.hideSubmitModal());
        }
        if (this.confirmSubmitBtn) {
            this.confirmSubmitBtn.addEventListener('click', () => this.submitTest());
        }

        this.renderPaletteButtons();
    }

    initTimer() {
        this.updateTimerDisplay();
        this.timerInterval = setInterval(() => {
            this.remainingSeconds--;
            this.updateTimerDisplay();

            if (this.remainingSeconds <= 120 && this.timerDisplay) {
                this.timerDisplay.classList.add('timer-danger');
            }

            if (this.remainingSeconds <= 0) {
                clearInterval(this.timerInterval);
                alert("Time is up! Your mock test is being submitted automatically.");
                this.submitTest();
            }
        }, 1000);
    }

    updateTimerDisplay() {
        if (!this.timerDisplay) return;
        const mins = Math.floor(Math.max(0, this.remainingSeconds) / 60);
        const secs = Math.max(0, this.remainingSeconds) % 60;
        this.timerDisplay.textContent = 
            `${String(mins).padStart(2, '0')}:${String(secs).padStart(2, '0')}`;
    }

    renderPaletteButtons() {
        if (!this.paletteGrid) return;
        this.paletteGrid.innerHTML = '';

        this.questions.forEach((q, idx) => {
            const btn = document.createElement('button');
            btn.type = 'button';
            btn.className = 'palette-btn';
            btn.textContent = idx + 1;
            btn.dataset.index = idx;
            btn.addEventListener('click', () => {
                this.renderQuestion(idx);
            });
            this.paletteGrid.appendChild(btn);
        });
    }

    renderQuestion(index) {
        if (index < 0 || index >= this.questions.length) return;
        this.currentIndex = index;
        const q = this.questions[index];

        if (this.qNumberEl) {
            this.qNumberEl.textContent = `Question ${index + 1} of ${this.questions.length}`;
        }

        if (this.qBodyEl) {
            this.qBodyEl.innerHTML = q.question;
        }

        if (this.qImageEl) {
            if (q.question_image) {
                this.qImageEl.src = `/uploads/questions/${q.question_image}`;
                this.qImageEl.style.display = 'block';
            } else {
                this.qImageEl.style.display = 'none';
            }
        }

        // Render Options A, B, C, D
        if (this.optionsContainer) {
            this.optionsContainer.innerHTML = '';
            const opts = [
                { letter: 'A', text: q.option_a, img: q.option_a_image },
                { letter: 'B', text: q.option_b, img: q.option_b_image },
                { letter: 'C', text: q.option_c, img: q.option_c_image },
                { letter: 'D', text: q.option_d, img: q.option_d_image }
            ];

            const selectedAnswer = this.answers[q.id];

            opts.forEach(opt => {
                const optEl = document.createElement('div');
                optEl.className = `cbt-option-item ${selectedAnswer === opt.letter ? 'selected' : ''}`;
                
                let imgHtml = opt.img ? `<div style="margin-top:8px;"><img src="/uploads/questions/${opt.img}" style="max-height:120px; border-radius:6px;"></div>` : '';

                optEl.innerHTML = `
                    <div class="cbt-option-letter">${opt.letter}</div>
                    <div class="cbt-option-text">
                        <div>${opt.text}</div>
                        ${imgHtml}
                    </div>
                `;

                optEl.addEventListener('click', () => {
                    this.selectAnswer(q.id, opt.letter);
                });

                this.optionsContainer.appendChild(optEl);
            });
        }

        // Update Prev / Next Buttons state
        if (this.prevBtn) this.prevBtn.disabled = (index === 0);
        if (this.nextBtn) {
            if (index === this.questions.length - 1) {
                this.nextBtn.textContent = 'Review & Submit';
            } else {
                this.nextBtn.textContent = 'Next Question →';
            }
        }

        // Update Review button label
        if (this.reviewBtn) {
            const isMarked = this.markedForReview[q.id];
            this.reviewBtn.textContent = isMarked ? '★ Unmark Review' : '☆ Mark for Review';
            this.reviewBtn.classList.toggle('btn-primary', isMarked);
            this.reviewBtn.classList.toggle('btn-secondary', !isMarked);
        }

        this.updatePalette();
        if (window.renderMath) window.renderMath();
    }

    selectAnswer(questionId, letter) {
        this.answers[questionId] = letter;
        this.renderQuestion(this.currentIndex);
    }

    clearAnswer() {
        const q = this.questions[this.currentIndex];
        delete this.answers[q.id];
        this.renderQuestion(this.currentIndex);
    }

    toggleReview() {
        const q = this.questions[this.currentIndex];
        this.markedForReview[q.id] = !this.markedForReview[q.id];
        this.renderQuestion(this.currentIndex);
    }

    navigate(direction) {
        const targetIndex = this.currentIndex + direction;
        if (targetIndex >= this.questions.length) {
            this.showSubmitModal();
        } else if (targetIndex >= 0) {
            this.renderQuestion(targetIndex);
        }
    }

    updatePalette() {
        if (!this.paletteGrid) return;
        const buttons = this.paletteGrid.querySelectorAll('.palette-btn');

        buttons.forEach((btn, idx) => {
            const q = this.questions[idx];
            const isAnswered = Boolean(this.answers[q.id]);
            const isMarked = Boolean(this.markedForReview[q.id]);
            const isCurrent = (idx === this.currentIndex);

            btn.className = 'palette-btn';
            if (isMarked) btn.classList.add('marked-review');
            else if (isAnswered) btn.classList.add('answered');

            if (isCurrent) btn.classList.add('current');
        });
    }

    showSubmitModal() {
        if (!this.submitModal) return;
        const total = this.questions.length;
        const answered = Object.keys(this.answers).length;
        const unanswered = total - answered;
        const marked = Object.values(this.markedForReview).filter(Boolean).length;

        document.getElementById('modalTotalQuestions').textContent = total;
        document.getElementById('modalAnsweredCount').textContent = answered;
        document.getElementById('modalUnansweredCount').textContent = unanswered;
        document.getElementById('modalMarkedCount').textContent = marked;

        this.submitModal.classList.add('active');
    }

    hideSubmitModal() {
        if (this.submitModal) this.submitModal.classList.remove('active');
    }

    submitTest() {
        clearInterval(this.timerInterval);
        if (!this.testForm) return;

        // Populate hidden inputs for each question
        this.questions.forEach(q => {
            let input = document.getElementById(`hidden_answer_${q.id}`);
            if (!input) {
                input = document.createElement('input');
                input.type = 'hidden';
                input.name = `answer_${q.id}`;
                input.id = `hidden_answer_${q.id}`;
                this.testForm.appendChild(input);
            }
            input.value = this.answers[q.id] || '';
        });

        this.testForm.submit();
    }
}

window.TestRunner = TestRunner;
