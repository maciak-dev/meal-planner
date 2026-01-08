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
        const res = await fetch("/recipes/");
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
    <p><strong>Description:</strong> ${r.description}</p>

    <p><strong>Ingredients:</strong></p>
    <div class="ingredients-list">
        ${renderIngredients(r.ingredients)}
    </div>


    <div class="recipe-actions">
        <button class="secondary"
        onclick="showInstructions('${r.instructions
            .replace(/'/g, "\\'")
            .replace(/\n/g, "<br>")}')">
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
        const res = await fetch(`/recipes/${recipeId}/visibility`, {
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



// === ADD RECIPE ===
async function addRecipe() {
    const recipe = {
        name: document.getElementById("name").value,
        description: document.getElementById("description").value,
        ingredients: document.getElementById("ingredients").value,
        instructions: document.getElementById("instructions").value
    };

    try {
        const res = await fetch("/recipes/", {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(recipe)
        });
        if (res.ok) {
            loadRecipes();
            ["name","description","ingredients","instructions"].forEach(id=>document.getElementById(id).value="");
            showToast("Recipe saved","success");
        } else showToast("Failed to save recipe","error");
    } catch (err) { console.error(err); showToast("Server error","warn"); }
}

// === EDIT RECIPE ===
let editingId = null;
function openEdit(id) {
    editingId = id;
    fetch(`/recipes/${id}`).then(r=>r.json()).then(r=>{
        document.getElementById("edit-name").value = r.name;
        document.getElementById("edit-description").value = r.description;
        document.getElementById("edit-ingredients").value = r.ingredients;
        document.getElementById("edit-instructions").value = r.instructions;
        document.getElementById("edit-modal").style.display="block";
    });
}
function closeEdit() { document.getElementById("edit-modal").style.display="none"; }

async function saveEdit() {
    if(!editingId) return;
    const recipe = {
        name: document.getElementById("edit-name").value,
        description: document.getElementById("edit-description").value,
        ingredients: document.getElementById("edit-ingredients").value,
        instructions: document.getElementById("edit-instructions").value
    };
    try {
        const res = await fetch(`/recipes/${editingId}`, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(recipe)
        });
        if(res.ok){ closeEdit(); loadRecipes(); showToast("Recipe updated","success"); }
        else showToast("Failed to update recipe","error");
    } catch(err){ console.error(err); showToast("Server error","warn"); }
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
        const res=await fetch(`/recipes/${deleteRecipeId}`,{method:"DELETE"});
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

function toggleShoppingMode() {
    shoppingMode = !shoppingMode;


    document.getElementById("shopping-input-box").style.display =
        shoppingMode ? "none" : "flex";

    updateShoppingTitle();
    renderShoppingList();
    showToast(
        shoppingMode ? "Shopping mode ON 🛒" : "Shopping mode OFF",
        "success"
    );
}

function getShoppingList() {
    return JSON.parse(
        localStorage.getItem("shoppingList") || "[]"
    );
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

function renderShoppingList() {
    const listEl = document.getElementById("shopping-list");
    const list = getShoppingList();

    listEl.innerHTML = "";

    if (list.length === 0) {
        listEl.innerHTML = `<p class="muted">Your shopping list is empty 🛒</p>`;
        return;
    }

    list.forEach((item, index) => {
const div = document.createElement("div");

div.className = `shopping-item ${item.done ? "done" : ""}`;
div.style.opacity = "0";



        div.innerHTML = `
            <div class="shopping-main">
                <label class="done-switch" style="${shoppingMode ? "" : "display:none"}">
                    <input type="checkbox" ${item.done ? "checked" : ""} 
                        onchange="event.stopPropagation();toggleDone(${index})"
                        ${!shoppingMode ? "disabled" : ""}>
                    <span class="done-slider"></span>
                </label>

                <span class="item-name">${item.name}</span>
            </div>

            <span class="item-qty">${item.qty}</span>
           
            <div class="qty-controls">
            ${shoppingMode ? "" : `
            <button class="qty-btn"
                onclick="event.stopPropagation(); decreaseQty(${index})"
                ${item.done || shoppingMode ? "disabled" : ""}>
                -
            </button>

            <button class="qty-btn"
                onclick="event.stopPropagation(); increaseQty(${index})"
                ${item.done || shoppingMode ? "disabled" : ""}>
                +
            </button>
            
            </div>
            `}
        `;

        listEl.appendChild(div);
        setTimeout(() => {
            div.style.opacity = "1";
        }, 10);
    });
}

/*function clearShoppingList() {
    if (!confirm("Clear shopping list?")) return;
    saveShoppingList([]);
    renderShoppingList();
}
*/
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

function increaseQty(index) {
    const list = getShoppingList();
    list[index].qty += 1;
    saveShoppingList(list);
    renderShoppingList();
}

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

function updateShoppingTitle() {
    const title = document.getElementById("shopping-title");
    if (!title) return;

    title.textContent = shoppingMode
        ? "Shopping mode"
        : "Your shopping list";
}

