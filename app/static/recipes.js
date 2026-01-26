let recipesCache = [];


// === COLLAPSIBLE FORM ===
const addBtn = document.getElementById("add-recipe-btn");
const addForm = document.getElementById("add-recipe-form");
addBtn.addEventListener("click", () => {
    addBtn.classList.toggle("active");
    addForm.style.display = addForm.style.display === "block" ? "none" : "block";
});

// === LOAD & DISPLAY RECIPES ===
let ingredientsMap = {};

async function loadIngredientsMap() {
    const res = await fetch("/ingredients/map");
    ingredientsMap = await res.json();
}

function renderIngredients(ingredients) {
    return ingredients.split("\n").map(ing => {
        const key = ing.trim().toLowerCase();
        const essential = ingredientsMap[key] ?? true; // domyślnie ważne

        return `
          <label class="ingredient" style="display:flex; align-items:center; gap:6px;">
            <input type="checkbox" class="shopping-item" ${essential ? "checked" : ""}>
            <span>${ing}</span>
          </label>
        `;
    }).join("");
}

async function loadRecipes() {
    try {
        await loadIngredientsMap();
        const res = await fetch("/api/v1/recipes/");
        const data = await res.json();
        recipesCache = data;
        displayRecipes(data);
    } catch (err) { console.error("Error loading recipes:", err); }
}

function displayRecipes(recipes) {
    const container = document.getElementById("recipes-container");
    container.innerHTML = "";

recipes.forEach(r => {
    const box = document.createElement("div");
    box.className = "recipe-box";
    box.innerHTML = `
<h3>${r.name}</h3>

<div class="recipe-body">

    <div class="recipe-text">
        <p><strong>Description:</strong> ${r.description}</p>

        <p><strong>Ingredients:</strong></p>
        <div class="ingredients-list">
            ${renderIngredients(r.ingredients)}
        </div>
    </div>

    ${r.image ? `
    <div class="recipe-image-wrap">
        <img src="${r.image}" class="recipe-image">
    </div>
    ` : ""}

</div>

<div class="recipe-actions">
    <button class="secondary"
        onclick="showInstructions('${r.instructions.replace(/'/g, "\\'").replace(/\n/g, "<br>")}')">
        View Instructions
    </button>

    <button class="secondary add-to-list"
        data-recipe-id="${r.id}"
        onclick="addRecipeToShoppingList(this)">
        + Add to list
    </button>

    <button class="secondary" onclick="openEdit(${r.id})">Edit</button>
    <button class="danger" onclick="openDeleteModal(${r.id}, '${r.name.replace(/'/g,"\\'")}')">Delete</button>
    ${renderVisibilitySwitch(r)}
</div>
`;
    container.appendChild(box);
});


}

async function toggleVisibility(recipeId, checkbox) {
    const newValue = checkbox.checked;

    try {
        const res = await fetch(`/api/v1/recipes/${recipeId}/visibility`, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify({ is_public: newValue })
        });

        if (!res.ok) {
            throw new Error("Forbidden");
        }
    } catch (err) {
        checkbox.checked = !newValue; // 👈 cofamy
        showToast("You cannot change visibility of this recipe");
    }
}

function renderVisibilitySwitch(recipe) {
    const disabled = recipe.is_owner === false ? "disabled" : "";

    return `
        <label class="visibility-switch ${disabled}">
            <input type="checkbox"
                ${recipe.is_public ? "checked" : ""}
                ${disabled}
                onchange="toggleVisibility(${recipe.id}, this)"
            >
            <span class="slider"></span>
            <span class="labels">
                <span class="private">PRIVATE</span>
                <span class="public">PUBLIC</span>
            </span>
        </label>
    `;
}

// ADD RECIPE

async function addRecipe() {
    const recipe = {
        name: document.getElementById("name").value,
        description: document.getElementById("description").value,
        ingredients: document.getElementById("ingredients").value,
        instructions: document.getElementById("instructions").value
    };

    try {
        const res = await fetch("/api/v1/recipes/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(recipe)
        });

        if (res.ok) {
            const data = await res.json();   // 👈 TU
            await uploadRecipeImage(data.id, "add-image"); // 👈 TU

            loadRecipes();
            ["name","description","ingredients","instructions"].forEach(id=>document.getElementById(id).value="");
            document.getElementById("add-preview").style.display="none";

            showToast("Recipe saved","success");
        } else {
            showToast("Failed to save recipe","error");
        }

    } catch (err) {
        console.error(err);
        showToast("Server error","warn");
    }
}

// EDIT RECIPE 
let editingId = null;

function openEdit(id) {
    console.log("open CLICKED");
    const recipe = recipesCache.find(r => r.id === id);
    if(!recipe) return;

    editingId = id;

    document.getElementById("edit-name").value = recipe.name || "";
    document.getElementById("edit-description").value = recipe.description || "";
    document.getElementById("edit-ingredients").value = recipe.ingredients || "";
    document.getElementById("edit-instructions").value = recipe.instructions || "";

    document.getElementById("edit-preview").src = recipe.image || "";
    document.getElementById("edit-preview").style.display = recipe.image ? "block" : "none";

 /*   document.getElementById("edit-image").value = ""; // 🔥 TO JEST KLUCZ */
    const file = document.getElementById("edit-image");
if (file) file.value = "";
    document.getElementById("edit-modal").style.display = "block";
}

async function saveEdit() {
    console.log("SAVE CLICKED");
    if (!editingId) return;

    const recipe = {
        name: document.getElementById("edit-name").value,
        description: document.getElementById("edit-description").value,
        ingredients: document.getElementById("edit-ingredients").value,
        instructions: document.getElementById("edit-instructions").value
    };

    try {
        // 1️⃣ Aktualizacja danych JSON
        const res = await fetch(`/api/v1/recipes/${editingId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(recipe)
        });

        if (res.ok) {
            // 2️⃣ Aktualizacja obrazka jeśli wybrano nowy plik
            await updateRecipeImage(editingId, "edit-image");

            editingId = null; // wyczyść
            closeEdit();
            loadRecipes();
            showToast("Recipe updated", "success");
        } else {
            showToast("Failed to update recipe", "error");
        }
    } catch (err) {
        console.error(err);
        showToast("Server error", "warn");
    }
}

function closeEdit() {
    document.body.classList.remove("modal-open");
    document.getElementById("edit-modal").style.display = "none";
    editingId = null;
}

// === DELETE RECIPE ===
let deleteRecipeId=null;
function openDeleteModal(id,name){
    deleteRecipeId=id;
    document.getElementById("delete-text").innerText=`Are you sure you want to delete "${name}"?`;
    document.getElementById("delete-modal").style.display="block";
}
function closeDeleteModal(){ deleteRecipeId=null; document.getElementById("delete-modal").style.display="none"; }

async function confirmDeleteYes(){
    if(!deleteRecipeId) return;
    try{
        const res=await fetch(`/api/v1/recipes/${deleteRecipeId}`,{method:"DELETE"});
        if(res.ok){ closeDeleteModal(); loadRecipes(); showToast("Recipe deleted","success"); }
        else showToast("Failed to delete recipe","error");
    }catch(err){ console.error(err); showToast("Server error","warn"); }
}

// === INSTRUCTIONS MODAL ===
function showInstructions(html){ 
    document.getElementById("modal-text").innerHTML = html;
    document.getElementById("modal").style.display = "block";
}

function closeModal(){
    document.getElementById("modal").style.display = "none";
}

// === TOAST ===
function showToast(msg,type="success"){
    const toast=document.getElementById("toast");
    toast.textContent=msg;
    toast.className=`toast ${type} show`;
    setTimeout(()=>{ toast.classList.remove("show"); },2500);
}

// === THEME ===
function setTheme(theme){
    document.body.classList.remove("theme-cyber","theme-scandi");
    document.body.classList.add(theme);
    localStorage.setItem("theme",theme);
}
function toggleTheme(){
    const current=document.body.classList.contains("theme-scandi")?"theme-scandi":"theme-cyber";
    setTheme(current==="theme-scandi"?"theme-cyber":"theme-scandi");
}
function filterRecipes() {
    const query = document.getElementById("search").value.toLowerCase();
    const recipes = document.querySelectorAll(".recipe-box");

    recipes.forEach(box => {
        const text = box.innerText.toLowerCase();
        box.style.display = text.includes(query) ? "block" : "none";
    });
}
// === ON LOAD ===
document.addEventListener("DOMContentLoaded", () => {
    loadRecipes();
    renderShoppingList();
    const saved = localStorage.getItem("theme") || "theme-cyber";
    setTheme(saved);

        const shoppingInput = document.getElementById("shopping-input");
    if (shoppingInput) {
        shoppingInput.addEventListener("keydown", e => {
            if (e.key === "Enter") {
                e.preventDefault();
                addShoppingItem();
            }
        });
    }
});


// === NEW MODULE
function showModule(name) {
    document.getElementById("recipes-module").style.display =
        name === "recipes" ? "block" : "none";

    document.getElementById("shopping-module").style.display =
        name === "shopping" ? "block" : "none";

    document.querySelectorAll(".nav-tab").forEach(btn =>
        btn.classList.remove("active")
    );

    document
        .querySelector(`[data-module="${name}"]`)
        .classList.add("active");

    if (name === "shopping") {
        renderShoppingList();
    }
}

/* SHOPPING LIST – TEMP */



let shoppingMode = false;
let shoppingFocus = false;
let pendingRemoveIndex = null;
let pendingRemoveTimer = null;

function toggleShoppingMode() {
    shoppingMode = !shoppingMode;
    shoppingFocus = shoppingMode;

    const module = document.getElementById("shopping-module");
    module.classList.toggle("shopping-active", shoppingMode);
    document.body.classList.toggle("shopping-active", shoppingMode); 
    updateShoppingTitle();
    renderShoppingList();

    showToast(
        shoppingMode ? "Shopping mode ON 🛒" : "Shopping mode OFF",
        "success"
    );
}


function getShoppingList() {
    try {
        const data = JSON.parse(localStorage.getItem("shoppingList") || "[]");

        // normalizacja + zabezpieczenie na stare dane
        return data.map(item => ({
            name: typeof item.name === "string" ? item.name : "Unknown",
            qty: typeof item.qty === "number" ? item.qty : 1,
            done: !!item.done
        }));
    } catch (e) {
        console.warn("Corrupted shoppingList, resetting…");
        localStorage.removeItem("shoppingList");
        return [];
    }
}


function saveShoppingList(list) {
    localStorage.setItem("shoppingList", JSON.stringify(list));
}


function addShoppingItem() {
    const input = document.getElementById("shopping-input");
    const value = input.value.trim();
    if (!value) return;

    const list = getShoppingList();
    const existing = list.find(i => i.name === value);

    if (existing) {
        existing.qty += 1;
    } else {
        list.push({ name: value, qty: 1 });
    }
    saveShoppingList(list);
    input.value = "";
    renderShoppingList();
}
function getPositions() {
    const items = document.querySelectorAll(".shopping-item");
    const map = new Map();

    items.forEach(el => {
        map.set(el.dataset.key, el.getBoundingClientRect());
    });

    return map;
}

function renderShoppingList() {
    const listEl = document.getElementById("shopping-list");
    const list = getShoppingList();

    // --- FLIP: zapamiętujemy stare pozycje ---
    const oldPositions = new Map();
    listEl.querySelectorAll(".shopping-item").forEach(el => {
        oldPositions.set(el.dataset.key, el.getBoundingClientRect());
    });

    // --- sortujemy kupione na dół ---
    const sortedList = [...list].sort((a, b) => a.done - b.done);

    listEl.innerHTML = "";
    if (sortedList.length === 0) {
        listEl.innerHTML = `<p class="muted">Your shopping list is empty 🛒</p>`;
        return;
    }

    sortedList.forEach((item, index) => {
        const div = document.createElement("div");
        div.className = `shopping-item ${item.done ? "done" : ""}`;
        div.dataset.key = item.name;

        div.innerHTML = `
            <div class="shopping-main">
                <label class="done-switch" style="${shoppingMode ? "" : "display:none"}">
                    <input type="checkbox" ${item.done ? "checked" : ""}
                        onchange="event.stopPropagation(); toggleDone(${index})">
                    <span class="done-slider"></span>
                </label>
                <span class="item-name">${item.name}</span>
            </div>

            <span class="item-qty">${item.qty}</span>

            ${shoppingMode ? "" : `
            <div class="qty-controls">
                <button class="qty-btn"
                    onclick="event.stopPropagation(); decreaseQty(${index})"
                    ${item.done ? "disabled" : ""}>-</button>
                <button class="qty-btn"
                    onclick="event.stopPropagation(); increaseQty(${index})"
                    ${item.done ? "disabled" : ""}>+</button>
            </div>
            `}
        `;

        listEl.appendChild(div);
        div.classList.add("just-added");
        setTimeout(() => div.classList.remove("just-added"), 600);
    });

    // --- FLIP animation ---
    requestAnimationFrame(() => {
        const newItems = listEl.querySelectorAll(".shopping-item");
        newItems.forEach(el => {
            const old = oldPositions.get(el.dataset.key);
            if (!old) return;

            const newPos = el.getBoundingClientRect();
            const dy = old.top - newPos.top;

            if (dy !== 0) {
                el.style.transform = `translateY(${dy}px)`;
                el.style.transition = "none";

                requestAnimationFrame(() => {
                    el.style.transition = "transform 300ms ease";
                    el.style.transform = "";
                });
            }
        });
    });
}

function clearShoppingList() {
    const modal = document.getElementById("clear-modal");
        document.getElementById("clear-title").innerText = "Clear shopping list";
    document.getElementById("clear-text").innerText =
        "Are you sure you want to clear the entire shopping list?";

    modal.dataset.action = "clear";
    modal.style.display = "flex"; // pokaz modal
}

function confirmClearYes() {
    const modal = document.getElementById("clear-modal");

    if (modal.dataset.action === "clear") {
        saveShoppingList([]);
        renderShoppingList();
        showToast("Shopping list cleared 🧹");
    }

    closeClearModal();
}

function closeClearModal() {
    const modal = document.getElementById("clear-modal");
    modal.style.display = "none";
}

function addRecipeToShoppingList(buttonEl) {
    // szukamy najbliższego recipe-box
    const recipeEl = buttonEl.closest(".recipe-box");
    if (!recipeEl) return;

    const checkboxes = recipeEl.querySelectorAll(
        ".ingredients-list input[type='checkbox']:checked"
    );

    const list = getShoppingList();

    checkboxes.forEach(cb => {
        const ingredientText = cb.nextElementSibling.textContent
            .trim()
            .toLowerCase();

        const existing = list.find(i => i.name === ingredientText);

        if (existing) {
            existing.qty += 1;
        } else {
            list.push({ name: ingredientText, qty: 1 });
        }
    });

    saveShoppingList(list);
    renderShoppingList();
    showToast("Selected ingredients added to shopping list 🛒");
}

/*
function increaseQty(index) {
    const list = getShoppingList();
    list[index].qty += 1;
    saveShoppingList(list);
    renderShoppingList();

    const rows = document.querySelectorAll(".shopping-item");
    const qty = rows[index]?.querySelector(".item-qty");
    if (qty) {
        qty.classList.add("bump");
        setTimeout(() => qty.classList.remove("bump"), 300);
    }
}
*/
/*
function increaseQty(index) {
    const list = getShoppingList();
    list[index].qty += 1;
    saveShoppingList(list);
    renderShoppingList();

        const rows = document.querySelectorAll(".shopping-item");
    const qty = rows[index]?.querySelector(".item-qty");
    if (qty) {
        qty.classList.add("bump");
        setTimeout(() => qty.classList.remove("bump"), 300);
    }
}
*/
/*
function decreaseQty(index) {
    const list = getShoppingList();

    if (list[index].qty > 1) {
        list[index].qty -= 1;
    } else {
        // jeśli qty = 1 → usuwamy pozycję
        list.splice(index, 1);
    }

    saveShoppingList(list);
    renderShoppingList();
}

*/
/*
function decreaseQty(index) {
    const list = getShoppingList();
    const item = list[index];

    if (item.qty > 1) {
        item.qty -= 1;
        saveShoppingList(list);
        renderShoppingList();
        return;
    }

    // qty == 1 → zabezpieczenie przed przypadkowym usunięciem
    if (pendingRemoveIndex === index) {
        // DRUGIE kliknięcie → usuwamy
        list.splice(index, 1);
        saveShoppingList(list);
        renderShoppingList();
        showToast(`${item.name} removed 🗑️`);

        pendingRemoveIndex = null;
        clearTimeout(pendingRemoveTimer);
        pendingRemoveTimer = null;
        return;
    }

    // PIERWSZE kliknięcie → ostrzegamy
    pendingRemoveIndex = index;
    showToast(`Tap again to remove ${item.name}`, "warn");

    pendingRemoveTimer = setTimeout(() => {
        pendingRemoveIndex = null;
    }, 2000); // 2 sekundy na decyzję
}
*/
function decreaseQty(index) {
    const list = getShoppingList();
    const item = list[index];

    if (item.qty > 1) {
        item.qty -= 1;
        saveShoppingList(list);
        renderShoppingList();
        return;
    }

    // qty == 1 → zabezpieczenie przed przypadkowym usunięciem
    if (pendingRemoveIndex === index) {
        // DRUGI klik → usuwamy
        list.splice(index, 1);
        saveShoppingList(list);
        renderShoppingList();
        showToast(`${item.name} removed 🗑️`);

        pendingRemoveIndex = null;
        clearTimeout(pendingRemoveTimer);
        pendingRemoveTimer = null;
        return;
    }

    // PIERWSZY klik → ostrzegamy
    pendingRemoveIndex = index;
    showToast(`Tap again to remove ${item.name}`, "warn");

    pendingRemoveTimer = setTimeout(() => {
        pendingRemoveIndex = null;
    }, 2000);
}
function toggleDone(index) {
    const list = getShoppingList();

    const item = list[index];
    item.done = !item.done;

    const moved = list.splice(index, 1)[0];

    if (item.done) {
        list.push(moved);
    } else {
        list.unshift(moved);
    }

    saveShoppingList(list);
    renderShoppingList();
}

function increaseQty(index) {
    const list = getShoppingList();
    const item = list[index];

    item.qty += 1;
    saveShoppingList(list);
    renderShoppingList();

    // 👇 po renderze znajdź TEN konkretny element po nazwie
    requestAnimationFrame(() => {
        const row = document.querySelector(
            `.shopping-item[data-key="${item.name}"] .item-qty`
        );

        if (row) {
            row.classList.add("bump");
            setTimeout(() => row.classList.remove("bump"), 300);
        }
    });
}


function updateShoppingTitle() {
    const title = document.getElementById("shopping-title");
    if (!title) return;

    title.textContent = shoppingMode
        ? "Shopping mode"
        : "Your shopping list";
}


function isMobile() {
    return window.matchMedia("(max-width: 700px)").matches;
}


function toggleModuleNav() {
    if (!isMobile()) return;

    const nav = document.querySelector(".module-nav");
    const isOpen = nav.classList.contains("open");

    closeAllMenus();

    if (!isOpen) {
        nav.classList.add("open");
    }
}

function closeAllMenus() {
    if (isMobile()) {
        document.querySelector(".module-nav")?.classList.remove("open");
    }

    const burger = document.getElementById("burger-menu");
    const burgerBtn = document.querySelector(".burger-btn");

    burger?.classList.remove("open");
    burgerBtn?.classList.remove("active");
}

function setupImagePreview(inputId, previewId) {
    const input = document.getElementById(inputId);
    const preview = document.getElementById(previewId);

    input.addEventListener("change", () => {
        const file = input.files[0];
        if (!file) return;

        const reader = new FileReader();
        reader.onload = e => {
            preview.src = e.target.result;
            preview.style.display = "block";
        };
        reader.readAsDataURL(file);
    });
}

setupImagePreview("add-image", "add-preview");
setupImagePreview("edit-image", "edit-preview");

async function uploadRecipeImage(recipeId, inputId) {
    const input = document.getElementById(inputId);
    if (!input.files.length) return;

    const formData = new FormData();
    formData.append("file", input.files[0]);

    await fetch(`/api/v1/recipes/${recipeId}/image`, {
        method: "PUT",
        body: formData
    });

    input.value = "";
}

async function updateRecipeImage(recipeId, inputId) {
    const input = document.getElementById(inputId);
    if (!input.files.length) return; // jeśli nie zmieniono obrazka, nie robimy requestu

    const formData = new FormData();
    formData.append("file", input.files[0]);

    try {
        const res = await fetch(`/api/v1/recipes/${recipeId}/image`, {
            method: "PUT",
            body: formData
        });

        if (!res.ok) showToast("Failed to update image", "error");
    } catch (err) {
        console.error(err);
        showToast("Server error", "warn");
    }
}



function removeAddImage(){
    const preview = document.getElementById("add-preview");
    const input = document.getElementById("add-image");

    preview.src = "";
    preview.style.display = "none";
    input.value = "";
}

function removeImage() {
    if (!editingId) return;

    fetch(`/api/v1/recipes/${editingId}/image`, {
        method: "DELETE"
    })
    .then(res => {
        if (!res.ok) throw new Error("Failed to delete image");
        return res.json();
    })
    .then(() => {
        const preview = document.getElementById("edit-preview");
        preview.src = "";
        preview.style.display = "none";

        document.getElementById("edit-image").value = "";

        showToast("Image removed", "success");
    })
    .catch(err => {
        console.error(err);
        showToast(err.message, "error");
    });
}


function openIngredientsModal(){
    showToast("Ingredients feature coming soon","info");
}


/*
function toggleBurger() {
    const burger = document.getElementById("burger-menu");
    burger.style.display = burger.style.display === "block" ? "none" : "block";
}





document.addEventListener("click", e => {
    const burger = document.getElementById("burger-menu");
    const burgerBtn = document.querySelector(".burger-btn");

    if (!burger || burger.style.display !== "block") return;

    if (
        burger.contains(e.target) ||
        burgerBtn.contains(e.target)
    ) return;

    closeBurger();
});


function closeBurger() {
    const burger = document.getElementById("burger-menu");
    burger.style.display = "none";
}
*/


function toggleBurger() {
    const burger = document.getElementById("burger-menu");
    const burgerBtn = document.querySelector(".burger-btn");
    const isOpen = burger.classList.contains("open");

    closeAllMenus();

    if (!isOpen) {
        burger.classList.add("open");
        burgerBtn.classList.add("active");
    }
}



document.addEventListener("click", e => {
    if (!isMobile()) return;

    const burger = document.getElementById("burger-menu");
    const burgerBtn = document.querySelector(".burger-btn");
    const moduleNav = document.querySelector(".module-nav");
    const title = document.querySelector(".topbar-left h1");

    if (
        burger?.contains(e.target) ||
        burgerBtn?.contains(e.target) ||
        moduleNav?.contains(e.target) ||
        title?.contains(e.target)
    ) return;

    closeAllMenus();
});

document.querySelector(".module-nav")?.addEventListener("click", e => {
    if (isMobile() && e.target.closest("button")) {
        closeAllMenus();
    }
});

document.getElementById("burger-menu")?.addEventListener("click", e => {
    if (e.target.closest("button")) {
        closeAllMenus();
    }
});