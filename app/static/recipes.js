
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
          <button class="secondary"
onclick="showInstructions('${r.instructions
    .replace(/'/g, "\\'")
    .replace(/\n/g, "<br>")}'
)">
    View Instructions
</button>

            <button class="secondary" onclick="openEdit(${r.id})">Edit</button>
            <button class="danger" onclick="openDeleteModal(${r.id},'${r.name.replace(/'/g,"\\'")}')">Delete</button>
        `;
        container.appendChild(box);
    });
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
document.addEventListener("DOMContentLoaded",()=>{ loadRecipes(); const saved=localStorage.getItem("theme")||"theme-cyber"; setTheme(saved); });
