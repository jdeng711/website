// Split-Flap Board JavaScript
const CHARS = 'ABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789@.-_/: ';

function createFlap(char = ' ') {
  const flap = document.createElement('div');
  flap.className = 'flap';
  flap.innerHTML = `
    <div class="flap-half flap-top">
      <div class="flap-content">${char}</div>
    </div>
    <div class="flap-half flap-bottom">
      <div class="flap-content">${char}</div>
    </div>
  `;
  return flap;
}

function setFlapChar(flap, newChar) {
  const topContent = flap.querySelector('.flap-top .flap-content');
  const bottomContent = flap.querySelector('.flap-bottom .flap-content');
  
  const currentChar = topContent.textContent;
  if (currentChar === newChar) return;

  flap.classList.add('flipping');
  
  setTimeout(() => {
    topContent.textContent = newChar;
    bottomContent.textContent = newChar;
    flap.classList.remove('flipping');
  }, 160);
}

function animateFlap(flap, targetChar, delay = 0) {
  setTimeout(() => {
    const randomFlips = 5 + Math.floor(Math.random() * 5);
    let count = 0;

    function flip() {
      if (count < randomFlips) {
        const randomChar = CHARS[Math.floor(Math.random() * CHARS.length)];
        setFlapChar(flap, randomChar);
        count++;
        setTimeout(flip, 170);
      } else {
        setTimeout(() => {
          setFlapChar(flap, targetChar);
        }, 170);
      }
    }

    flip();
  }, delay);
}

function initSplitFlapBoard(data) {
  Object.keys(data).forEach((key, rowIndex) => {
    const container = document.getElementById(key);
    if (!container) return;
    
    const text = data[key].substring(0, 25).padEnd(25, ' ');
    
    const flaps = [];
    for (let i = 0; i < 25; i++) {
      const flap = createFlap(' ');
      flaps.push(flap);
      container.appendChild(flap);
    }

    // Animate each character with stagger
    flaps.forEach((flap, i) => {
      const char = text[i];
      const delay = (rowIndex * 400) + (i * 50);
      animateFlap(flap, char, delay);
    });
  });
}

// Initialize on page load
document.addEventListener('DOMContentLoaded', () => {
  const data = {
    location: 'SHENYANG, CHINA',
    email: 'JDENG@COLLEGE.HARVARD.EDU',
    status: 'UNDERGRADUATE @ HARVARD'
  };
  
  initSplitFlapBoard(data);
});