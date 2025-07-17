// Import the functions you need from the SDKs you need
import { initializeApp } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-app.js";
import { getAnalytics } from "https://www.gstatic.com/firebasejs/11.10.0/firebase-analytics.js";
import {
  getFirestore,
  collection,
  getDocs,
  query,
  orderBy,
} from "https://www.gstatic.com/firebasejs/11.10.0/firebase-firestore.js";
// TODO: Add SDKs for Firebase products that you want to use
// https://firebase.google.com/docs/web/setup#available-libraries

// Your web app's Firebase configuration
// For Firebase JS SDK v7.20.0 and later, measurementId is optional
const firebaseConfig = {
  apiKey: "AIzaSyC1XsUtd7BCDJAGUeRsj81i4b2-Y9V6Se0",
  authDomain: "ai-news-d366b.firebaseapp.com",
  projectId: "ai-news-d366b",
  storageBucket: "ai-news-d366b.appspot.com",
  messagingSenderId: "394345339711",
  appId: "1:394345339711:web:67352738a2fd682247118a",
  measurementId: "G-W9X9PY6G9E",
};

// Initialize Firebase
const app = initializeApp(firebaseConfig);
const analytics = getAnalytics(app);
const db = getFirestore(app);

// 分頁相關變量
const ITEMS_PER_PAGE = 20;
let currentPage = 1;
let totalPages = 1;
let allArticles = [];
let currentPageArticles = [];
let ap = null; // 音頻播放器實例

// 從 Firestore 讀取文章
async function loadArticles() {
  try {
    const articles = [];
    const papersCol = collection(db, "papers");
    const q = query(papersCol, orderBy("published_date", "desc"));
    const querySnapshot = await getDocs(q);
    querySnapshot.forEach((doc) => {
      articles.push(doc.data());
    });
    return articles;
  } catch (error) {
    console.error("從 Firestore 載入文章失敗:", error);
    return [];
  }
}

// 分頁相關函數
function getCurrentPageArticles(page) {
  const startIndex = (page - 1) * ITEMS_PER_PAGE;
  const endIndex = startIndex + ITEMS_PER_PAGE;
  return allArticles.slice(startIndex, endIndex);
}

function updatePaginationInfo() {
  const startIndex = (currentPage - 1) * ITEMS_PER_PAGE + 1;
  const endIndex = Math.min(currentPage * ITEMS_PER_PAGE, allArticles.length);
  const infoText = `顯示第 ${startIndex}-${endIndex} 則論文，共 ${allArticles.length} 則`;
  document.getElementById("pagination-info-text").textContent = infoText;
}

function generatePageNumbers() {
  const pageNumbersContainer = document.getElementById("page-numbers");
  pageNumbersContainer.innerHTML = "";

  // 計算要顯示的頁碼範圍
  const maxVisiblePages = 7;
  let startPage = Math.max(1, currentPage - Math.floor(maxVisiblePages / 2));
  let endPage = Math.min(totalPages, startPage + maxVisiblePages - 1);

  // 調整起始頁碼
  if (endPage - startPage + 1 < maxVisiblePages) {
    startPage = Math.max(1, endPage - maxVisiblePages + 1);
  }

  // 如果起始頁碼不是1，顯示第一頁和省略號
  if (startPage > 1) {
    const firstPageBtn = createPageButton(1);
    pageNumbersContainer.appendChild(firstPageBtn);

    if (startPage > 2) {
      const ellipsis = document.createElement("span");
      ellipsis.className = "page-ellipsis";
      ellipsis.textContent = "...";
      pageNumbersContainer.appendChild(ellipsis);
    }
  }

  // 顯示頁碼按鈕
  for (let i = startPage; i <= endPage; i++) {
    const pageBtn = createPageButton(i);
    pageNumbersContainer.appendChild(pageBtn);
  }

  // 如果結束頁碼不是最後一頁，顯示省略號和最後一頁
  if (endPage < totalPages) {
    if (endPage < totalPages - 1) {
      const ellipsis = document.createElement("span");
      ellipsis.className = "page-ellipsis";
      ellipsis.textContent = "...";
      pageNumbersContainer.appendChild(ellipsis);
    }

    const lastPageBtn = createPageButton(totalPages);
    pageNumbersContainer.appendChild(lastPageBtn);
  }
}

function createPageButton(page) {
  const button = document.createElement("button");
  button.className = "page-btn";
  button.textContent = page;
  if (page === currentPage) {
    button.classList.add("active");
  }
  button.addEventListener("click", () => goToPage(page));
  return button;
}

function goToPage(page) {
  if (page < 1 || page > totalPages || page === currentPage) return;

  currentPage = page;
  currentPageArticles = getCurrentPageArticles(currentPage);

  // 更新文章顯示
  displayArticles();

  // 更新分頁信息和導航
  updatePaginationInfo();
  generatePageNumbers();
  updateNavigationButtons();

  // 更新音頻播放器
  updateAudioPlayer();

  // 滾動到頂部
  window.scrollTo({ top: 0, behavior: "smooth" });
}

function updateNavigationButtons() {
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");

  prevBtn.disabled = currentPage === 1;
  nextBtn.disabled = currentPage === totalPages;
}

// 建立音訊播放列表
function createAudioList(articles) {
  // 過濾掉沒有有效音訊連結的文章，然後建立播放列表
  return articles
    .filter(
      (article) => article.audio_url && article.audio_url.startsWith("http")
    )
    .map((article) => {
      const authors = Array.isArray(article.authors)
        ? article.authors.join("、")
        : article.authors;

      return {
        name: article.title_zh,
        artist: authors,
        url: article.audio_url, // 直接使用文章資料中的音訊 URL
        cover:
          "https://raw.githubusercontent.com/DIYgod/APlayer/master/assets/default.jpg",
      };
    });
}

// 建立文章 HTML
function createArticleHTML(article) {
  const authors = Array.isArray(article.authors)
    ? article.authors.join("、")
    : article.authors;
  const topic = article.query
    ? `<span class="topic">${article.query}</span>`
    : "";

  // 處理生活化應用場景
  let applicationsHTML = "";
  if (article.applications && Array.isArray(article.applications)) {
    applicationsHTML = `
      <div class="applications">
        <h3>生活化應用場景</h3>
        <ul>
          ${article.applications.map((app) => `<li>${app}</li>`).join("")}
        </ul>
      </div>
    `;
  }

  // 處理創投推銷內容
  let pitchHTML = "";
  if (article.pitch) {
    pitchHTML = `
      <div class="pitch">
        <h3>創投推銷角度</h3>
        <p>${article.pitch}</p>
      </div>
    `;
  }

  return `
        <div class="article" data-audio-id="${article.arxiv_id}">
            ${topic ? `<div class="topic-row">${topic}</div>` : ""}
            <div class="title">
                <a class="title-original" href="${
                  article.arxiv_url
                }" target="_blank" style="display:none;">${article.title}</a>
                <a class="title-translation" href="${
                  article.arxiv_url
                }" target="_blank">${article.title_zh}</a>
            </div>
            <div class="meta">${authors} ｜ ${article.published_date}</div>
            <div class="abstract">
                <span class="abstract-original" style="display:none;">${
                  article.summary
                }</span>
                <span class="abstract-translation">${article.summary_zh}</span>
            </div>
            ${applicationsHTML}
            ${pitchHTML}
        </div>
    `;
}

// 顯示文章
function displayArticles() {
  const container = document.getElementById("articles-container");
  container.innerHTML = currentPageArticles.map(createArticleHTML).join("");

  // 重新綁定中英文切換功能
  applyLanguageToggle();
}

// 更新音頻播放器
function updateAudioPlayer() {
  if (ap) {
    // 更新播放列表
    ap.list.clear();
    const audioList = createAudioList(currentPageArticles);
    ap.list.add(audioList);
  }
}

// 初始化分頁導航事件
function initializePagination() {
  const prevBtn = document.getElementById("prev-btn");
  const nextBtn = document.getElementById("next-btn");

  prevBtn.addEventListener("click", () => goToPage(currentPage - 1));
  nextBtn.addEventListener("click", () => goToPage(currentPage + 1));
}

// 應用語言切換狀態
function applyLanguageToggle() {
  document
    .querySelectorAll(".title-original")
    .forEach((e) => (e.style.display = showingTranslation ? "none" : ""));
  document
    .querySelectorAll(".title-translation")
    .forEach((e) => (e.style.display = showingTranslation ? "" : "none"));
  document
    .querySelectorAll(".abstract-original")
    .forEach((e) => (e.style.display = showingTranslation ? "none" : ""));
  document
    .querySelectorAll(".abstract-translation")
    .forEach((e) => (e.style.display = showingTranslation ? "" : "none"));
}

// 初始化頁面
async function initializePage() {
  // 載入所有文章
  allArticles = await loadArticles();

  // 計算總頁數
  totalPages = Math.ceil(allArticles.length / ITEMS_PER_PAGE);

  // 獲取第一頁文章
  currentPageArticles = getCurrentPageArticles(1);

  // 初始化音訊播放器
  ap = new APlayer({
    container: document.getElementById("aplayer"),
    audio: createAudioList(currentPageArticles),
    theme: "#6366f1",
    lrcType: 0,
    listFolded: false,
    listMaxHeight: 200,
    order: "list",
    controls: ["prev", "play", "next", "progress", "volume", "list"],
  });

  // 顯示文章
  displayArticles();

  // 初始化分頁
  updatePaginationInfo();
  generatePageNumbers();
  updateNavigationButtons();
  initializePagination();

  // 播放速度控制
  const defaultSpeed = 1.0;
  let currentSpeed = defaultSpeed;

  // 設定初始播放速度
  if (ap.audio) {
    ap.audio.playbackRate = defaultSpeed;
  }

  // 當播放器載入新的音訊時，設定播放速度
  ap.on("canplay", () => {
    if (ap.audio) {
      ap.audio.playbackRate = currentSpeed;
    }
  });

  // 添加點擊事件到播放速度按鈕
  document.querySelectorAll(".speed-btn").forEach((btn) => {
    btn.addEventListener("click", () => {
      const speed = parseFloat(btn.getAttribute("data-speed"));

      // 更新播放速度
      currentSpeed = speed;
      if (ap.audio) {
        ap.audio.playbackRate = speed;
      }

      // 更新按鈕樣式
      document.querySelectorAll(".speed-btn").forEach((b) => {
        b.classList.remove("active");
      });
      btn.classList.add("active");
    });
  });

  // 監聽播放器事件
  function updateCurrentArticle() {
    const currentAudio = ap.list.audios[ap.list.index];
    // 從 URL 中提取檔案名稱，移除路徑和副檔名
    const currentId = currentAudio.url.split("/").pop().replace(".wav", "");

    // 移除所有文章的 playing 類別
    document.querySelectorAll(".article").forEach((article) => {
      article.classList.remove("playing");
    });

    // 為當前播放的文章添加 playing 類別
    const currentArticle = document.querySelector(
      `.article[data-audio-id="${currentId}"]`
    );
    if (currentArticle) {
      currentArticle.classList.add("playing");
      // 平滑滾動到當前文章
      setTimeout(() => {
        currentArticle.scrollIntoView({ behavior: "smooth", block: "start" });
      }, 300);
    }
  }

  // 監聽播放和切換曲目事件
  ap.on("play", updateCurrentArticle);
  ap.on("listswitch", updateCurrentArticle);

  // 綁定切換按鈕事件
  bindToggleButton();
}

// 切換中英文顯示
let showingTranslation = true;
function toggleAll() {
  showingTranslation = !showingTranslation;
  const btn = document.getElementById("toggle-all-btn");

  // 應用語言切換狀態
  applyLanguageToggle();

  // 更新按鈕文字
  btn.textContent = showingTranslation ? "顯示原文" : "顯示翻譯";
}

// 綁定按鈕事件
function bindToggleButton() {
  const btn = document.getElementById("toggle-all-btn");
  btn.addEventListener("click", toggleAll);
}

// 當頁面載入完成時初始化
document.addEventListener("DOMContentLoaded", initializePage);
