// ===============================
// CONFIG
// ===============================

const STORAGE_KEY = "verseid_admin_key";

const API_BASE = `${window.location.origin}/api/v1`;

let signupsChart = null;
let searchesChart = null;

// ===============================
// DOM
// ===============================

const menuToggle = document.getElementById("menuToggle");
const sidebar = document.getElementById("sidebar");
const refreshBtn = document.getElementById("refreshBtn");

const statsGrid = document.getElementById("statsGrid");

const lastUpdated = document.getElementById("lastUpdated");

// ===============================
// MOBILE SIDEBAR
// ===============================

menuToggle.addEventListener("click", () => {

    sidebar.classList.toggle("open");

});

// ===============================
// ADMIN KEY
// ===============================

function getKey() {

    return localStorage.getItem(STORAGE_KEY);

}

// ===============================
// REFRESH
// ===============================

refreshBtn.addEventListener("click", () => {

    loadDashboard();

});

// ===============================
// LOAD DASHBOARD
// ===============================

async function loadDashboard() {

    const key = getKey();

    if (!key) {

        alert("No admin key found.");

        return;

    }

    try {

        const response = await fetch(

            `${API_BASE}/admin/stats/`,

            {

                headers: {

                    "X-Admin-Key": key

                }

            }

        );

        if (response.status === 403) {

            alert("Invalid Admin Key");

            return;

        }

        const data = await response.json();

        renderDashboard(data);

    }

    catch(error){

        console.error(error);

        alert("Unable to load dashboard.");

    }

}

// ===============================
// RENDER
// ===============================

function renderDashboard(data){

    lastUpdated.textContent =

        new Date(

            data.generatedAt

        ).toLocaleTimeString();

    renderCards(

        data.totals

    );

}

// ===============================
// KPI CARDS
// ===============================

function renderCards(t){

    const cards = [

        {

            icon:"👥",

            title:"Users",

            value:t.users,

            change:`+${t.newToday} today`

        },

        {

            icon:"🔍",

            title:"Searches",

            value:t.totalSearches,

            change:`${t.searchesToday} today`

        },

        {

            icon:"💜",

            title:"Pro Users",

            value:t.proUsers,

            change:`${t.freeUsers} Free`

        },

        {

            icon:"💳",

            title:"Subscriptions",

            value:t.activeSubscriptions,

            change:"Active"

        },

        {

            icon:"📖",

            title:"Saved",

            value:t.totalSaved,

            change:"Bookmarks"

        },

        {

            icon:"🟢",

            title:"Google",

            value:t.googleSignups,

            change:`${t.emailSignups} Email`

        },

        {

            icon:"⚡",

            title:"Active 7d",

            value:t.activeLast7Days,

            change:"Recently Active"

        },

        {

            icon:"📅",

            title:"This Week",

            value:t.newThisWeek,

            change:"New Users"

        },

        {

            icon:"📈",

            title:"This Month",

            value:t.newThisMonth,

            change:"Growth"

        },

        {

            icon:"💰",

            title:"MRR",

            value:"₦"+Number(

                t.mrrNaira

            ).toLocaleString(),

            change:"Monthly"

        }

    ];

    statsGrid.innerHTML =

        cards.map(card=>`

            <div class="stat-card">

                <div class="stat-title">

                    ${card.icon}

                    ${card.title}

                </div>

                <div class="stat-value">

                    ${card.value}

                </div>

                <div class="stat-change">

                    ${card.change}

                </div>

            </div>

        `).join("");

}

// ===============================
// INIT
// ===============================

loadDashboard();