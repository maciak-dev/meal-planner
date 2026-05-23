const Api = {
    async request(url, options = {}) {
        const res = await fetch(url, options);

        if (!res.ok) {
            let msg = "API error";
            try {
                msg = await res.text();
            } catch { }
            throw new Error(msg || "API error");
        }

        return res;
    },

    get(url) {
        return this.request(url);
    },

    post(url, data) {
        return this.request(url, {
            method: "POST",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    put(url, data) {
        return this.request(url, {
            method: "PUT",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    patch(url, data) {
        return this.request(url, {
            method: "PATCH",
            headers: { "Content-Type": "application/json" },
            body: JSON.stringify(data)
        });
    },

    delete(url) {
        return this.request(url, { method: "DELETE" });
    },

    upload(url, formData) {
        return this.request(url, {
            method: "PUT",
            body: formData
        });
    }
};

const UI = {
    toast(msg, type = "success", timeout = 2500) {
        const toast = document.getElementById("toast");
        if (!toast) return;

        toast.textContent = msg;
        toast.className = `toast ${type} show`;

        clearTimeout(this._toastTimer);
        this._toastTimer = setTimeout(
            () => toast.classList.remove("show"),
            timeout
        );
    },

    openModal(id) {
        document.body.classList.add("modal-open");
        document.getElementById(id)?.classList.add("open");
    },

    closeModal(id) {
        document.body.classList.remove("modal-open");
        document.getElementById(id)?.classList.remove("open");
    },

    theme: {
        set(theme) {
            document.body.classList.remove("theme-cyber", "theme-scandi");
            document.body.classList.add(theme);
            localStorage.setItem("theme", theme);
        },

        toggle() {
            const current = document.body.classList.contains("theme-scandi")
                ? "theme-scandi"
                : "theme-cyber";
            this.set(current === "theme-scandi" ? "theme-cyber" : "theme-scandi");
        },

        load() {
            this.set(localStorage.getItem("theme") || "theme-cyber");
        }
    }

};

const RecipesUI = {
    add: {
        name: () => document.getElementById("name"),
        description: () => document.getElementById("description"),
        ingredients: () => document.getElementById("ingredients"),
        instructions: () => document.getElementById("instructions"),
        preview: () => document.getElementById("add-preview"),
        image: () => document.getElementById("add-image"),
        form: () => document.getElementById("add-recipe-form")
    },
    edit: {
        name: () => document.getElementById("edit-name"),
        description: () => document.getElementById("edit-description"),
        ingredients: () => document.getElementById("edit-ingredients"),
        instructions: () => document.getElementById("edit-instructions"),
        preview: () => document.getElementById("edit-preview"),
        image: () => document.getElementById("edit-image"),
        modal: () => document.getElementById("edit-modal")
    },
    list: () => document.getElementById("recipes-container")
};

function clearForm(fields) {
    Object.values(fields)
        .map(fn => fn())
        .filter(el => el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA"))
        .forEach(el => el.value = "");
}


const Recipes = {
    state: {
        cache: [],
        ingredientsMap: {}
    },

    async load() {
        try {
            const mapRes = await Api.get("/ingredients/map");
            this.state.ingredientsMap = await mapRes.json();

            const res = await Api.get("/api/v1/recipes/");
            const data = await res.json();

            this.state.cache = data;
            this.render(data);

        } catch (err) {
            console.error("Error loading recipes:", err);
        }
    },

    renderRecipeBadge(recipe) {
    if (recipe.is_owner) {
        return `
            <span class="recipe-badge mine ${recipe.is_public ? "public" : "private"}">
                MY · ${recipe.is_public ? "PUBLIC" : "PRIVATE"}
            </span>
        `;
    }

    return `
        <span class="recipe-badge foreign">
            BY ${recipe.author_username ?? "USER"}
        </span>
    `;
    },


    render(recipes) {
        const container = RecipesUI.list();
        container.innerHTML = "";
        recipes.forEach(r => {
            const isOwner = r.is_owner === true;
            const box = document.createElement("div");
            box.className = "recipe-box";
            box.innerHTML = `
            <div class="recipe-header">
                <h3>${r.name}</h3>
                ${this.renderRecipeBadge(r)}
            </div>
            <div class="recipe-body">
            <div class="recipe-text">
                <p><strong>Description:</strong> ${r.description}</p>
                <p><strong>Ingredients:</strong></p>
                <div class="ingredients-list">
                    ${this.renderIngredients(r.ingredients)}
                </div>
            </div>
            ${r.image ? `
            <div class="recipe-image-wrap">
                <img src="${r.image}" class="recipe-image">
            </div>
            ` : ""}
            </div>
                <div class="recipe-actions">
    <!-- ZAWSZE -->
    <button class="secondary"
        data-action="instructions"
        data-instructions="${r.instructions}">
        View Instructions
    </button>

    <button class="secondary add-to-list"
        data-action="add-to-list"
        data-id="${r.id}">
        + Add to list
    </button>

    <!-- TYLKO WŁAŚCICIEL -->
    ${isOwner ? `
        <button class="secondary"
            data-action="edit"
            data-id="${r.id}">
            Manage
        </button>




    ` : ""}
</div>

            `;
            container.appendChild(box);
        });
    },

    renderIngredients(ingredients) {
        return ingredients.split("\n").map(ing => {
            const key = ing.trim().toLowerCase();
            const essential = this.state.ingredientsMap[key] ?? true;

            return `
          <label class="ingredient" style="display:flex; align-items:center; gap:6px;">
            <input type="checkbox" class="shopping-item" ${essential ? "checked" : ""}>
            <span>${ing}</span>
          </label>
        `;
        }).join("");
    },

    actions: {
        edit(id) {
            Recipes.actions.openEdit(id);
        },

        delete(id, name) {
            openDeleteModal(id, name);
        },

        addToList(btn) {
            addRecipeToShoppingList(btn);
        },

        instructions(text) {
            showInstructions(text);
        },

        create() {
            const recipe = {
                name: RecipesUI.add.name().value,
                description: RecipesUI.add.description().value,
                ingredients: RecipesUI.add.ingredients().value,
                instructions: RecipesUI.add.instructions().value
            };

            Api.post("/api/v1/recipes/", recipe)
                .then(res => res.json())
                .then(data => uploadRecipeImage(data.id, "add-image"))
                .then(() => {
                    Recipes.load();
                    clearForm(RecipesUI.add);
                    RecipesUI.add.preview().style.display = "none";
                    RecipesUI.add.image().value = "";

                    UI.toast("Recipe saved", "success");
                })
                .catch(err => {
                    console.error(err);
                    UI.toast("Server error", "warn");
                });
        },
        openEdit(id) {
            const recipe = Recipes.state.cache.find(r => r.id === id);
            if (!recipe) return;

            editingId = id;

            RecipesUI.edit.name().value = recipe.name || "";
            document.getElementById("edit-is-public").checked = recipe.is_public;
            RecipesUI.edit.description().value = recipe.description || "";
            RecipesUI.edit.ingredients().value = recipe.ingredients || "";
            RecipesUI.edit.instructions().value = recipe.instructions || "";
            
            const preview = RecipesUI.edit.preview();
            preview.src = recipe.image || "";
            preview.style.display = recipe.image ? "block" : "none";

            const file = RecipesUI.edit.image();
            if (file) file.value = "";

            UI.openModal("edit-modal");
        },
        async update() {
            if (!editingId) return;

            try {
                const recipe = {
                    name: RecipesUI.edit.name().value,
                    is_public: document.getElementById("edit-is-public").checked,
                    description: RecipesUI.edit.description().value,
                    ingredients: RecipesUI.edit.ingredients().value,
                    instructions: RecipesUI.edit.instructions().value
                };

                await Api.put(`/api/v1/recipes/${editingId}`, recipe);
                await updateRecipeImage(editingId, "edit-image");

                editingId = null;
                closeEdit();
                await Recipes.load();

                UI.toast("Recipe updated", "success");
            } catch (err) {
                console.error(err);
                UI.toast("Server error", "warn");
            }
        },

        toggleVisibility(id, checkbox) {
            Api.patch(`/api/v1/recipes/${id}/visibility`, { is_public: checkbox.checked })
                .catch(() => {
                    checkbox.checked = !checkbox.checked;
                    UI.toast("You cannot change visibility of this recipe");
                });
        }

    },

    handleClick(e) {
        const btn = e.target.closest("button");
        if (!btn) return;

        const action = btn.dataset.action;
        if (!action) return;

        const map = {
            edit: () => this.actions.edit(Number(btn.dataset.id)),
            delete: () => this.actions.delete(Number(btn.dataset.id), btn.dataset.name),
            "add-to-list": () => this.actions.addToList(btn),
            instructions: () => this.actions.instructions(btn.dataset.instructions || "")
        };

        map[action]?.();
    },

    handleChange(e) {
        const input = e.target;
        const action = input.dataset.action;
        if (!action) return;

        if (action === "visibility") {
            this.actions.toggleVisibility(Number(input.dataset.id), input);
        }
    },
    handleFormClick(e) {
    const btn = e.target.closest("button");
    if (!btn) return;

    const action = btn.dataset.action;
    if (!action) return;

    const map = {
        "create-recipe": () => this.actions.create(),

        "update-recipe": () => this.actions.update(),

        "delete": () =>
            this.actions.delete(
                editingId,
                RecipesUI.edit.name().value
            )
    };

    map[action]?.();
}



};


const ShoppingUI = {
    list: () => document.getElementById("shopping-list"),
    input: () => document.getElementById("shopping-input"),
    title: () => document.getElementById("shopping-title"),
    module: () => document.getElementById("shopping-module"),
    clearModal: () => document.getElementById("clear-modal"),

    importBtn: () => document.getElementById("open-shopping-import-btn")
};


const Shopping = {
    state: {
        mode: false,
        focus: false,
        pendingRemoveId: null,
        pendingRemoveTimer: null
    },
    getList() {
        try {
            const data = JSON.parse(localStorage.getItem("shoppingList") || "[]");
            return data.map(item => ({
                id: item.id || crypto.randomUUID(),
                name: typeof item.name === "string" ? item.name : "Unknown",
                qty: typeof item.qty === "number" ? item.qty : 1,
                done: !!item.done
            }));
        } catch (e) {
            console.warn("Corrupted shoppingList, resetting…");
            localStorage.removeItem("shoppingList");
            return [];
        }
    },
    saveList(list) {
        localStorage.setItem("shoppingList", JSON.stringify(list));
    },
    updateImportButton() {
    const btn = ShoppingUI.importBtn();

    if (!btn) return;

    const shouldShow = !Shopping.state.mode;

    btn.style.display = shouldShow
        ? "inline-flex"
        : "none";
    },
    render() {
        const listEl = ShoppingUI.list();
        const list = this.getList();
        const oldPositions = new Map();
        listEl.querySelectorAll(".shopping-item").forEach(el => {
            oldPositions.set(el.dataset.id, el.getBoundingClientRect());
        });
        const sortedList = [...list].sort((a, b) => a.done - b.done);
        listEl.innerHTML = "";
        if (sortedList.length === 0) {
            listEl.innerHTML = `<p class="muted">Your shopping list is empty 🛒</p>`;
            return;
        }
        sortedList.forEach(item => {
            const div = document.createElement("div");
            div.className = `shopping-item ${item.done ? "done" : ""}`;
            div.dataset.id = item.id;
            div.innerHTML = `
                <div class="shopping-main">
                    <label class="done-switch" style="${this.state.mode ? "" : "display:none"}">
                        <input type="checkbox" ${item.done ? "checked" : ""}
                            data-action="toggle-done"
                            data-id="${item.id}">
                        <span class="done-slider"></span>
                    </label>
                    <span class="item-name">${item.name}</span>
                </div>
                <span class="item-qty">${item.qty}</span>
                ${this.state.mode ? "" : `
                <div class="qty-controls">
                    <button class="qty-btn"
                        data-action="decrease"
                        data-id="${item.id}"
                        ${item.done ? "disabled" : ""}>-</button>

                    <button class="qty-btn"
                        data-action="increase"
                        data-id="${item.id}"
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
                const old = oldPositions.get(el.dataset.id);
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
    },
    actions: {
        increase(id) {
            const list = Shopping.getList();
            const item = list.find(i => i.id === id);
            if (!item) return;

            item.qty += 1;
            Shopping.saveList(list);
            Shopping.render();

            requestAnimationFrame(() => {
                const row = document.querySelector(
                    `.shopping-item[data-id="${id}"] .item-qty`
                );

                if (row) {
                    row.classList.add("bump");
                    setTimeout(() => row.classList.remove("bump"), 300);
                }
            });
        },

        decrease(id) {
            const list = Shopping.getList();
            const index = list.findIndex(i => i.id === id);
            if (index === -1) return;

            const item = list[index];

            if (item.qty > 1) {
                item.qty -= 1;
                Shopping.saveList(list);
                Shopping.render();
                return;
            }

            // zabezpieczenie przed przypadkowym usunięciem
            if (Shopping.state.pendingRemoveId === id) {
                list.splice(index, 1);
                Shopping.saveList(list);
                Shopping.render();
                UI.toast(`${item.name} removed 🗑️`);

                Shopping.state.pendingRemoveId = null;
                clearTimeout(Shopping.state.pendingRemoveTimer);
                Shopping.state.pendingRemoveTimer = null;
                return;
            }

            Shopping.state.pendingRemoveId = id;
            UI.toast(`Tap again to remove ${item.name}`, "warn");

            Shopping.state.pendingRemoveTimer = setTimeout(() => {
                Shopping.state.pendingRemoveId = null;
            }, 2000);
        },

        toggleDone(id) {
            const list = Shopping.getList();
            const index = list.findIndex(i => i.id === id);
            if (index === -1) return;

            const item = list[index];
            item.done = !item.done;

            const moved = list.splice(index, 1)[0];

            if (item.done) {
                list.push(moved);
            } else {
                list.unshift(moved);
            }

            Shopping.saveList(list);
            Shopping.render();
        }
    },
    handleClick(e) {
        const btn = e.target.closest("button");
        if (!btn) return;

        const action = btn.dataset.action;
        if (!action) return;

        const map = {
            increase: id => this.actions.increase(id),
            decrease: id => this.actions.decrease(id)
        };

        const handler = map[action];
        if (handler) {
            handler(btn.dataset.id);
        }
    },

    handleChange(e) {
        const input = e.target;
        const action = input.dataset.action;
        if (!action) return;

        const map = {
            "toggle-done": id => this.actions.toggleDone(id)
        };

        const handler = map[action];
        if (handler) {
            handler(input.dataset.id);
        }
    },
    toggleMode() {
        Shopping.state.mode = !Shopping.state.mode;
        Shopping.state.focus = Shopping.state.mode;

        ShoppingUI.module().classList.toggle(
            "shopping-active",
            Shopping.state.mode
        );
        document.body.classList.toggle(
            "shopping-active",
            Shopping.state.mode
        );

        Shopping.updateTitle();
        Shopping.render();

        Shopping.updateImportButton();

        UI.toast(
            Shopping.state.mode ? "Shopping mode ON 🛒" : "Shopping mode OFF",
            "success"
        );
    },

    updateTitle() {
        ShoppingUI.title().textContent =
            Shopping.state.mode ? "Shopping mode" : "Your shopping list";
    },
    clear() {
        this.saveList([]);
        this.render();
        UI.toast("Shopping list cleared 🧹");
    }
};


const App = {
    init() {
        UI.theme.load();
        Recipes.load();
        Shopping.render();
        Shopping.updateImportButton();
        this.bindEvents();
    },


    handleGlobalClick(e) {
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
        ) {
            return;
        }

        closeAllMenus();
    },

    bindEvents() {
        // shopping input (Enter)
        const shoppingInput = document.getElementById("shopping-input");
        if (shoppingInput) {
            shoppingInput.addEventListener("keydown", e => {
                if (e.key === "Enter") {
                    e.preventDefault();
                    Shopping.addItem();
                }
            });
        }

        // shopping list
        const shoppingList = document.getElementById("shopping-list");
        if (shoppingList) {
            shoppingList.addEventListener("click", e => Shopping.handleClick(e));
            shoppingList.addEventListener("change", e => Shopping.handleChange(e));
        }

        // recipes list
        const recipesContainer = document.getElementById("recipes-container");
        if (recipesContainer) {
            recipesContainer.addEventListener("click", e => Recipes.handleClick(e));
            recipesContainer.addEventListener("change", e => Recipes.handleChange(e));
        }

        // recipe forms
        const addForm = document.getElementById("add-recipe-form");
        if (addForm) {
            addForm.addEventListener("click", e =>
                Recipes.handleFormClick(e)
            );
        }

        const editForm = document.getElementById("edit-modal");
        if (editForm) {
            editForm.addEventListener("click", e =>
                Recipes.handleFormClick(e)
            );
        }

        const themeBtn = document.getElementById("theme-toggle");
        if (themeBtn) {
            themeBtn.addEventListener("click", () => UI.theme.toggle());
        }


        document.addEventListener("click", e => App.handleGlobalClick(e));
    }

};





// === COLLAPSIBLE FORM ===
const addBtn = document.getElementById("add-recipe-btn");
const addForm = document.getElementById("add-recipe-form");
addBtn.addEventListener("click", () => {
    addBtn.classList.toggle("active");
    addForm.style.display = addForm.style.display === "block" ? "none" : "block";
});

// === LOAD & DISPLAY RECIPES ===


async function toggleVisibility(recipeId, checkbox) {
    const newValue = checkbox.checked;

    try {
        await Api.patch(`/api/v1/recipes/${recipeId}/visibility`, { is_public: newValue });


    } catch (err) {
        checkbox.checked = !newValue; // 👈 cofamy
        UI.toast("You cannot change visibility of this recipe");
    }
}

function renderVisibilitySwitch(recipe) {
    if (recipe.is_owner !== true) return "";

    return `
        <label class="visibility-switch">
            <input type="checkbox"
                ${recipe.is_public ? "checked" : ""}
                data-action="visibility"
                data-id="${recipe.id}"
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




// EDIT RECIPE 
let editingId = null;


function closeEdit() {
    UI.closeModal("edit-modal");
    editingId = null;
}


// === DELETE RECIPE ===
let deleteRecipeId = null;
function openDeleteModal(id, name) {
    deleteRecipeId = id;
    document.getElementById("delete-text").innerText = `Are you sure you want to delete "${name}"?`;
    UI.openModal("delete-modal");
}
function closeDeleteModal() { deleteRecipeId = null; UI.closeModal("delete-modal"); }

async function confirmDeleteYes() {
    if (!deleteRecipeId) return;
    try {
        await Api.delete(`/api/v1/recipes/${deleteRecipeId}`);


        closeDeleteModal();
        closeEdit();
        Recipes.load();
        UI.toast("Recipe deleted", "success");

    } catch (err) { console.error(err); UI.toast("Server error", "warn"); }
}

// === INSTRUCTIONS MODAL ===
function showInstructions(text) {
    const modalText = document.getElementById("modal-text");

    // zamieniamy newline na <br> TUTAJ, bez hacków w HTML
    modalText.innerHTML = text
        .split("\n")
        .map(line => line.trim())
        .join("<br>");

    UI.openModal("modal");
}

function closeModal() {
    UI.closeModal("modal");

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
    App.init();
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
        Shopping.render();
    }
}

/* SHOPPING LIST – TEMP */
/*
function toggleShoppingMode() {
    Shopping.state.mode = !Shopping.state.mode;
    Shopping.state.focus = Shopping.state.mode;

    const module = document.getElementById("shopping-module");
    module.classList.toggle("shopping-active", Shopping.state.mode);
    document.body.classList.toggle("shopping-active", Shopping.state.mode);
    updateShoppingTitle();
    Shopping.render();

    UI.toast(
        Shopping.state.mode ? "Shopping mode ON 🛒" : "Shopping mode OFF",
        "success"
    );
}
*/
function toggleShoppingMode() {
    Shopping.toggleMode();
}

function addShoppingItem() {
    const input = ShoppingUI.input();
    const value = input.value.trim();
    if (!value) return;

    const list = Shopping.getList();
    const existing = list.find(i => i.name === value);

    if (existing) {
        existing.qty += 1;
    } else {
        list.push({ id: crypto.randomUUID(), name: value, qty: 1, done: false });
    }
    Shopping.saveList(list);
    input.value = "";
    Shopping.render();
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
    Shopping.clear();
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

    const list = Shopping.getList();

    checkboxes.forEach(cb => {
        const ingredientText = cb.nextElementSibling.textContent
            .trim()
            .toLowerCase();

        const existing = list.find(i => i.name === ingredientText);

        if (existing) {
            existing.qty += 1;
        } else {
            list.push({ id: crypto.randomUUID(), name: ingredientText, qty: 1, done: false });
        }
    });

    Shopping.saveList(list);
    Shopping.render();
    UI.toast("Selected ingredients added to shopping list 🛒");
}

function updateShoppingTitle() {
    const title = document.getElementById("shopping-title");
    if (!title) return;

    title.textContent = Shopping.state.mode
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

    await Api.upload(`/api/v1/recipes/${recipeId}/image`, formData);


    input.value = "";
}

async function updateRecipeImage(recipeId, inputId) {
    const input = document.getElementById(inputId);
    if (!input.files.length) return; // jeśli nie zmieniono obrazka, nie robimy requestu

    const formData = new FormData();
    formData.append("file", input.files[0]);

    try {
        await Api.upload(`/api/v1/recipes/${recipeId}/image`, formData);

    } catch (err) {
        console.error(err);
        UI.toast("Failed to update image", "error");
    }
}


function removeAddImage() {
    const preview = document.getElementById("add-preview");
    const input = document.getElementById("add-image");

    preview.src = "";
    preview.style.display = "none";
    input.value = "";
}


async function removeImage() {
    if (!editingId) return;

    try {
        await Api.delete(`/api/v1/recipes/${editingId}/image`);


        const preview = document.getElementById("edit-preview");
        preview.src = "";
        preview.style.display = "none";
        document.getElementById("edit-image").value = "";

        UI.toast("Image removed", "success");
    } catch (err) {
        console.error(err);
        UI.toast(err.message, "error");
    }
}


function openIngredientsModal() {
    UI.toast("Ingredients feature coming soon", "info");
}


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

function openShoppingImportModal() {
    const modal = document.getElementById("shopping-import-modal");

    if (!modal) {
        console.error("shopping-import-modal not found");
        return;
    }

    modal.classList.add("open");
    document.body.classList.add("modal-open");
}

function closeShoppingImportModal() {
    const modal = document.getElementById("shopping-import-modal");

    if (!modal) {
        console.error("shopping-import-modal not found");
        return;
    }

    modal.classList.remove("open");
    document.body.classList.remove("modal-open");
}

/* =========================
   SHOPPING IMPORT EVENTS
   ========================= */

const openShoppingImportBtn = document.getElementById(
    "open-shopping-import-btn"
);

if (openShoppingImportBtn) {
    openShoppingImportBtn.addEventListener(
        "click",
        openShoppingImportModal
    );
}

const closeShoppingImportBtn = document.getElementById(
    "close-shopping-import-modal"
);
const confirmShoppingImportBtn = document.getElementById(
    "confirm-shopping-import-btn"
);

if (confirmShoppingImportBtn) {
    confirmShoppingImportBtn.addEventListener(
        "click",
        importShoppingList
    );
}

if (closeShoppingImportBtn) {
    closeShoppingImportBtn.addEventListener(
        "click",
        closeShoppingImportModal
    );
}

function importShoppingList() {
    const textarea = document.getElementById(
        "shopping-import-textarea"
    );

    if (!textarea) {
        console.error("shopping-import-textarea not found");
        return;
    }

    const value = textarea.value.trim();

    if (!value) {
        UI.toast("Paste shopping list first", "warn");
        return;
    }

    const lines = value
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean);

    if (!lines.length) {
        UI.toast("Nothing to import", "warn");
        return;
    }

    const list = Shopping.getList();

    lines.forEach(itemName => {
        const normalized = itemName.toLowerCase();

        const existing = list.find(
            item => item.name.toLowerCase() === normalized
        );

        if (existing) {
            existing.qty += 1;
        } else {
            list.push({
                id: crypto.randomUUID(),
                name: itemName,
                qty: 1,
                done: false
            });
        }
    });

    Shopping.saveList(list);
    Shopping.render();

    textarea.value = "";

    closeShoppingImportModal();

    UI.toast("Shopping list imported 🛒", "success");
}