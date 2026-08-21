/**
 * Tłumaczenie stringów interfejsu po stronie klienta.
 *
 * Słownik przychodzi z serwera jako window.I18N - to ten sam plik JSON, z
 * którego korzysta Jinja, więc string istnieje w repozytorium dokładnie raz.
 *
 * Fallback jest celowo cichy: brakujący klucz zwraca sam klucz zamiast rzucać.
 * Widoczny klucz to defekt kosmetyczny, a wyjątek w środku renderowania listy
 * zakupów wywaliłby cały widok.
 *
 * Interpolacja {name} podmienia wyłącznie znane parametry i NIE parsuje HTML -
 * wynik trafia dalej przez textContent, zgodnie z zasadą z PR #15.
 */
function t(key, params) {
    const dict = window.I18N || {};
    let text = Object.prototype.hasOwnProperty.call(dict, key) ? dict[key] : key;

    if (params) {
        for (const [name, value] of Object.entries(params)) {
            text = text.split(`{${name}}`).join(String(value));
        }
    }
    return text;
}

const Api = {
    async request(url, options = {}) {
        const res = await fetch(url, options);

        if (!res.ok) {
            let msg = t("toast.api_error");
            try {
                msg = await res.text();
            } catch { }
            const error = new Error(msg || t("toast.api_error"));
            error.name = "ApiError";
            error.status = res.status;
            throw error;
        }

        return res;
    },

    get(url, options = {}) {
        return this.request(url, options);
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
        /* Kolejność definiuje też cykl przełączania (toggle). Nowe motywy
           dopisujemy tutaj + blok body.theme-* w themes.css. */
        THEMES: ["theme-cyber", "theme-light", "theme-map"],
        LEGACY_ALIASES: { "theme-scandi": "theme-light" },

        /* Motyw dla nowych użytkowników i brakującej/niepoprawnej wartości
           w localStorage. Zapisany wybór użytkownika ma priorytet - to pole
           dotyczy tylko przypadku, gdy nie ma nic do respektowania. */
        DEFAULT: "theme-map",

        set(theme) {
            theme = this.LEGACY_ALIASES[theme] || theme;
            if (!this.THEMES.includes(theme)) theme = this.DEFAULT;
            document.body.classList.remove(...this.THEMES, "theme-scandi");
            document.body.classList.add(theme);
            // MAP Light reuses the canonical MAP geometry/state selectors;
            // the light token layer below supplies only luminance changes.
            if (theme === "theme-light") document.body.classList.add("theme-map");
            localStorage.setItem("theme", theme);
            this.syncSwitcher(theme);
        },

        current() {
            if (document.body.classList.contains("theme-light")) return "theme-light";
            return this.THEMES.find(t => document.body.classList.contains(t)) || this.DEFAULT;
        },

        /* Zachowane dla zgodności (pojedynczy przycisk = cykl przez motywy). */
        toggle() {
            const next = (this.THEMES.indexOf(this.current()) + 1) % this.THEMES.length;
            this.set(this.THEMES[next]);
        },

        load() {
            this.set(localStorage.getItem("theme") || this.DEFAULT);
        },

        /* Podświetla aktywny motyw w przełączniku (burger menu). */
        syncSwitcher(theme) {
            document.querySelectorAll("[data-theme-option]").forEach(btn => {
                const active = btn.dataset.themeOption === theme;
                btn.classList.toggle("active", active);
                btn.setAttribute("aria-pressed", String(active));
            });
        }
    }

};

/**
 * Tworzy element z klasą i tekstem.
 *
 * Treść przepisu (nazwa, opis, instrukcje, składniki) pochodzi od użytkownika i
 * może być pokazana innym użytkownikom, gdy przepis jest publiczny. Nie wolno
 * jej skleić w string i oddać do innerHTML - `textContent` nigdy nie parsuje
 * HTML, więc znaczniki i handlery zdarzeń zostają zwykłym tekstem.
 */
function el(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text !== undefined && text !== null) node.textContent = String(text);
    return node;
}

const RecipesUI = {
    add: {
        name: () => document.getElementById("name"),
        description: () => document.getElementById("description"),
        ingredients: () => document.getElementById("ingredients"),
        instructions: () => document.getElementById("instructions"),
        preview: () => document.getElementById("add-preview"),
        image: () => document.getElementById("add-image"),
        isPublic: () => document.getElementById("add-is-public"),
        form: () => document.getElementById("add-recipe-form")
    },
    edit: {
        name: () => document.getElementById("edit-name"),
        description: () => document.getElementById("edit-description"),
        ingredients: () => document.getElementById("edit-ingredients"),
        instructions: () => document.getElementById("edit-instructions"),
        preview: () => document.getElementById("edit-preview"),
        image: () => document.getElementById("edit-image"),
        isPublic: () => document.getElementById("edit-is-public"),
        modal: () => document.getElementById("edit-modal")
    },
    list: () => document.getElementById("recipes-container")
};

function clearForm(fields) {
    Object.values(fields)
        .map(fn => fn())
        .filter(el => el && (el.tagName === "INPUT" || el.tagName === "TEXTAREA"))
        .forEach(el => {
            // Checkboxa nie czyści się przez .value - trzeba go odznaczyć, inaczej
            // przełącznik widoczności zostaje włączony po zapisaniu przepisu i
            // następny przepis dostaje ustawienie, którego nikt nie wybrał.
            if (el.type === "checkbox") {
                el.checked = false;
                return;
            }
            el.value = "";
        });
}


const Recipes = {
    state: {
        cache: [],
        ingredientsMap: {},
        page: 0,
        pageSize: 24,
        hasNext: true,
        loading: false,
        query: "",
        requestId: 0,
        controller: null,
        ingredientsLoaded: false
    },

    async load({ reset = true, query = this.state.query } = {}) {
        if (reset) {
            this.state.controller?.abort();
            this.state.controller = new AbortController();
            this.state.requestId += 1;
            this.state.page = 0;
            this.state.hasNext = true;
            this.state.query = query.trim();
            this.state.cache = [];
            this.render([]);
        } else if (this.state.loading || !this.state.hasNext) {
            return;
        }

        const requestId = this.state.requestId;
        const page = this.state.page + 1;
        this.state.loading = true;
        this.renderStatus(page === 1 ? "loading" : "loading-more");
        try {
            if (!this.state.ingredientsLoaded) {
                const mapRes = await Api.get("/ingredients/map", { signal: this.state.controller.signal });
                this.state.ingredientsMap = await mapRes.json();
                this.state.ingredientsLoaded = true;
            }

            const params = new URLSearchParams({ page: String(page), page_size: String(this.state.pageSize) });
            if (this.state.query) params.set("search", this.state.query);
            const res = await Api.get(`/api/v1/recipes/?${params.toString()}`, { signal: this.state.controller.signal });
            const data = await res.json();

            if (requestId !== this.state.requestId) return;
            const known = new Set(this.state.cache.map(recipe => recipe.id));
            const fresh = data.filter(recipe => !known.has(recipe.id));
            this.state.cache.push(...fresh);
            this.state.page = page;
            this.state.hasNext = res.headers.get("X-Recipes-Has-Next") === "true";
            this.render(fresh, { append: page > 1 });
            this.renderStatus(this.state.cache.length === 0 ? "empty" : this.state.hasNext ? "ready" : "end");

        } catch (err) {
            if (err.name === "AbortError" || requestId !== this.state.requestId) return;
            console.error("Error loading recipes:", err);
            this.renderStatus("error");
        } finally {
            if (requestId === this.state.requestId) this.state.loading = false;
        }
    },

    loadNext() {
        return this.load({ reset: false });
    },

    renderRecipeBadge(recipe) {
        if (recipe.is_owner) {
            const visibility = recipe.is_public
                ? t("recipes.visibility_public")
                : t("recipes.visibility_private");

            return el(
                "span",
                `recipe-badge mine ${recipe.is_public ? "public" : "private"}`,
                `${t("recipes.badge.mine_prefix")} ${visibility}`
            );
        }

        // author_username przychodzi z bazy i trafia na kartę cudzego przepisu.
        return el(
            "span",
            "recipe-badge foreign",
            `${t("recipes.badge.by_prefix")} ${recipe.author_username ?? t("recipes.badge.unknown_user")}`
        );
    },


    render(recipes, { append = false } = {}) {
        const container = RecipesUI.list();
        if (!append) container.replaceChildren();
        recipes.forEach(r => container.appendChild(this.renderRecipeCard(r)));
    },

    renderStatus(state) {
        const status = document.getElementById("recipes-status");
        if (!status) return;
        const messages = {
            loading: t("recipes.loading"),
            "loading-more": t("recipes.loading_more"),
            empty: t("recipes.empty"),
            end: t("recipes.end"),
            error: t("recipes.load_error"),
            ready: ""
        };
        status.replaceChildren();
        if (state === "error") {
            status.appendChild(el("span", null, messages.error));
            const retry = el("button", "secondary", t("common.retry"));
            retry.type = "button";
            retry.addEventListener("click", () => this.load({ reset: true }));
            status.appendChild(retry);
        } else {
            status.textContent = messages[state] || "";
        }
        status.classList.toggle("error", state === "error");
    },

    /**
     * Buduje kartę przepisu wyłącznie przez DOM API.
     *
     * Każde pole pochodzące od użytkownika (name, description, instructions,
     * ingredients, author_username, image) wchodzi przez textContent, dataset
     * albo właściwość elementu - nigdy przez sklejanie HTML-a. Nazwy klas i
     * struktura są takie same jak w poprzedniej wersji szablonowej, żeby CSS i
     * delegacja zdarzeń działały bez zmian.
     */
    renderRecipeCard(r) {
        const box = el("div", "recipe-box");

        const header = el("div", "recipe-header");
        header.appendChild(el("h3", null, r.name ?? ""));
        header.appendChild(this.renderRecipeBadge(r));
        box.appendChild(header);

        const body = el("div", "recipe-body");
        const textCol = el("div", "recipe-text");

        const description = el("p");
        description.appendChild(el("strong", null, t("recipes.card.description_label")));
        description.appendChild(document.createTextNode(` ${r.description ?? ""}`));
        textCol.appendChild(description);

        const ingredientsLabel = el("p");
        ingredientsLabel.appendChild(el("strong", null, t("recipes.card.ingredients_label")));
        textCol.appendChild(ingredientsLabel);

        textCol.appendChild(this.renderIngredients(r.ingredients));
        body.appendChild(textCol);

        if (r.image) {
            const imageWrap = el("div", "recipe-image-wrap");
            const image = el("img", "recipe-image");
            // .src jako właściwość: ścieżka nigdy nie jest parsowana jako HTML,
            // więc nie da się nią wyjść z atrybutu.
            image.src = r.image;
            imageWrap.appendChild(image);
            body.appendChild(imageWrap);
        }
        box.appendChild(body);

        const actions = el("div", "recipe-actions");

        const instructionsBtn = el("button", "secondary", t("recipes.card.view_instructions"));
        instructionsBtn.dataset.action = "instructions";
        // dataset zapisuje wartość atrybutu bez parsowania - cudzysłowy i znaczniki
        // w instrukcjach nie mają jak z niego wyjść.
        instructionsBtn.dataset.instructions = r.instructions ?? "";
        actions.appendChild(instructionsBtn);

        const addToListBtn = el("button", "secondary add-to-list", t("recipes.card.add_to_list"));
        addToListBtn.dataset.action = "add-to-list";
        addToListBtn.dataset.id = String(r.id);
        actions.appendChild(addToListBtn);

        if (r.is_owner === true) {
            const manageBtn = el("button", "secondary", t("recipes.card.manage"));
            manageBtn.dataset.action = "edit";
            manageBtn.dataset.id = String(r.id);
            actions.appendChild(manageBtn);
        }

        box.appendChild(actions);
        return box;
    },

    renderIngredients(ingredients) {
        const wrapper = el("div", "ingredients-list");

        (ingredients ?? "").split("\n").forEach(ing => {
            const key = ing.trim().toLowerCase();
            const essential = this.state.ingredientsMap[key] ?? true;

            const label = el("label", "ingredient");
            label.style.display = "flex";
            label.style.alignItems = "center";
            label.style.gap = "6px";

            const checkbox = el("input", "shopping-item");
            checkbox.type = "checkbox";
            checkbox.checked = essential;
            label.appendChild(checkbox);

            // Musi zostać <span> tuż za checkboxem - addRecipeToShoppingList()
            // czyta nazwę składnika przez cb.nextElementSibling.textContent.
            label.appendChild(el("span", null, ing));
            wrapper.appendChild(label);
        });

        return wrapper;
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
                instructions: RecipesUI.add.instructions().value,
                // Bez tego formularz zbierał wartość przełącznika widoczności i
                // ją wyrzucał - każdy nowy przepis wychodził prywatny.
                is_public: RecipesUI.add.isPublic().checked
            };

            Api.post("/api/v1/recipes/", recipe)
                .then(res => res.json())
                .then(data => uploadRecipeImage(data.id, "add-image"))
                .then(() => {
                    Recipes.load({ reset: true });
                    clearForm(RecipesUI.add);
                    RecipesUI.add.preview().style.display = "none";
                    RecipesUI.add.image().value = "";

                    UI.toast(t("toast.recipe_saved"), "success");
                })
                .catch(err => {
                    console.error(err);
                    UI.toast(t("toast.server_error"), "warn");
                });
        },
        openEdit(id) {
            const recipe = Recipes.state.cache.find(r => r.id === id);
            if (!recipe) return;

            editingId = id;

            RecipesUI.edit.name().value = recipe.name || "";
            RecipesUI.edit.isPublic().checked = recipe.is_public;
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
                    is_public: RecipesUI.edit.isPublic().checked,
                    description: RecipesUI.edit.description().value,
                    ingredients: RecipesUI.edit.ingredients().value,
                    instructions: RecipesUI.edit.instructions().value
                };

                await Api.put(`/api/v1/recipes/${editingId}`, recipe);
                await updateRecipeImage(editingId, "edit-image");

                editingId = null;
                closeEdit();
                await Recipes.load({ reset: true });

                UI.toast(t("toast.recipe_updated"), "success");
            } catch (err) {
                console.error(err);
                UI.toast(t("toast.server_error"), "warn");
            }
        },

        toggleVisibility(id, checkbox) {
            Api.patch(`/api/v1/recipes/${id}/visibility`, { is_public: checkbox.checked })
                .catch(() => {
                    checkbox.checked = !checkbox.checked;
                    UI.toast(t("toast.cannot_change_visibility"));
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
                name: typeof item.name === "string" ? item.name : t("shopping.unknown_item"),
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
        const sortedList = StoreLayouts.sortItems(list);
        listEl.replaceChildren();
        if (sortedList.length === 0) {
            listEl.appendChild(el("p", "muted", t("shopping.empty_state")));
            return;
        }
        sortedList.forEach(item => {
            // item.name to linia składnika przepisu, więc na liście zakupów ląduje
            // ta sama niezaufana treść co na karcie przepisu.
            const div = el("div", `shopping-item ${item.done ? "done" : ""}`);
            div.dataset.id = item.id;

            const main = el("div", "shopping-main");

            const doneSwitch = el("label", "done-switch");
            if (!this.state.mode) doneSwitch.style.display = "none";

            const doneCheckbox = document.createElement("input");
            doneCheckbox.type = "checkbox";
            doneCheckbox.checked = !!item.done;
            doneCheckbox.dataset.action = "toggle-done";
            doneCheckbox.dataset.id = item.id;
            doneSwitch.appendChild(doneCheckbox);
            doneSwitch.appendChild(el("span", "done-slider"));

            main.appendChild(doneSwitch);
            main.appendChild(el("span", "item-name", item.name));
            div.appendChild(main);

            div.appendChild(el("span", "item-qty", item.qty));

            if (!this.state.mode) {
                const controls = el("div", "qty-controls");

                [["decrease", "-"], ["increase", "+"]].forEach(([action, label]) => {
                    const btn = el("button", "qty-btn", label);
                    btn.dataset.action = action;
                    btn.dataset.id = item.id;
                    btn.disabled = !!item.done;
                    controls.appendChild(btn);
                });

                div.appendChild(controls);
            }

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
                UI.toast(t("toast.item_removed", { name: item.name }));

                Shopping.state.pendingRemoveId = null;
                clearTimeout(Shopping.state.pendingRemoveTimer);
                Shopping.state.pendingRemoveTimer = null;
                return;
            }

            Shopping.state.pendingRemoveId = id;
            UI.toast(t("toast.tap_again_remove", { name: item.name }), "warn");

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
            Shopping.state.mode ? t("toast.shopping_mode_on") : t("toast.shopping_mode_off"),
            "success"
        );
    },

    updateTitle() {
        ShoppingUI.title().textContent =
            Shopping.state.mode ? t("shopping.title_mode") : t("shopping.title_default");
    },
    clear() {
        this.saveList([]);
        this.render();
        UI.toast(t("toast.shopping_cleared"));
    }
};


const StoreLayouts = {
    state: { stores: [], ingredients: [], layouts: new Map(), activeStoreId: null },
    norm(value) { return String(value || "").trim().toLocaleLowerCase().replace(/\s+/g, " "); },
    async load() {
        try {
            const [storesResponse, ingredientsResponse] = await Promise.all([
                Api.get("/api/v1/stores"), Api.get("/api/v1/ingredients")
            ]);
            this.state.stores = await storesResponse.json();
            this.state.ingredients = await ingredientsResponse.json();
            const saved = localStorage.getItem("activeShoppingStoreId");
            this.state.activeStoreId = saved && this.state.stores.some(s => String(s.id) === saved) ? Number(saved) : null;
            this.renderStoreChoices();
            if (this.state.activeStoreId) await this.loadLayout(this.state.activeStoreId);
        } catch (err) { console.error("Error loading store layouts:", err); }
    },
    async loadLayout(storeId) {
        if (!storeId) return;
        const response = await Api.get(`/api/v1/stores/${storeId}/layout`);
        const layout = await response.json();
        this.state.layouts.set(Number(storeId), layout);
        this.renderStoreChoices();
        this.renderEditor();
        Shopping.render();
    },
    renderStoreChoices() {
        [document.getElementById("shopping-store-select"), document.getElementById("store-layout-select")].forEach(select => {
            if (!select) return;
            const current = String(this.state.activeStoreId || "");
            select.replaceChildren();
            if (select.id === "shopping-store-select") {
                const none = el("option", null, t("shop.no_store")); none.value = ""; select.appendChild(none);
            }
            this.state.stores.forEach(store => { const option = el("option", null, store.name); option.value = String(store.id); option.selected = String(store.id) === current; select.appendChild(option); });
        });
        const rename = document.getElementById("store-rename");
        const selected = this.state.stores.find(store => store.id === Number(this.state.activeStoreId));
        if (rename && selected) rename.value = selected.name;
    },
    selectStore(value) {
        this.state.activeStoreId = value ? Number(value) : null;
        if (this.state.activeStoreId) localStorage.setItem("activeShoppingStoreId", String(this.state.activeStoreId));
        else localStorage.removeItem("activeShoppingStoreId");
        this.renderStoreChoices();
        if (this.state.activeStoreId) this.loadLayout(this.state.activeStoreId);
        Shopping.render();
    },
    sortItems(items) {
        const layout = this.state.layouts.get(Number(this.state.activeStoreId));
        if (!layout) return [...items].sort((a, b) => a.done - b.done);
        const sections = new Map(layout.sections.map(s => [s.id, s.position]));
        const placements = new Map(layout.placements.map(p => [p.ingredient_id, p]));
        const names = new Map();
        this.state.ingredients.forEach(i => [i.name, i.canonical_name_pl, i.canonical_name_en].filter(Boolean).forEach(n => names.set(this.norm(n), i.id)));
        return [...items].map((item, index) => {
            const ingredientId = names.get(this.norm(item.name));
            const placement = placements.get(ingredientId);
            const rank = placement ? [0, sections.get(placement.store_section_id) ?? 10**9, placement.position ?? 10**9, index] : [1, 0, 0, index];
            return { item, index, rank };
        }).sort((a, b) => a.item.done - b.item.done || a.rank[0] - b.rank[0] || a.rank[1] - b.rank[1] || a.rank[2] - b.rank[2] || a.rank[3] - b.rank[3]).map(x => x.item);
    },
    renderEditor() {
        const list = document.getElementById("store-layout-list"); if (!list) return;
        list.replaceChildren();
        const layout = this.state.layouts.get(Number(this.state.activeStoreId));
        if (!layout) { list.appendChild(el("p", "muted", t("shop.choose_store"))); return; }
        layout.sections.forEach((section, index) => {
            const row = el("div", "shop-catalog-row"); row.appendChild(el("span", null, `${section.position + 1}. ${section.name}`));
            [ ["↑", index > 0 ? section.position - 1 : null], ["↓", index < layout.sections.length - 1 ? section.position + 1 : null] ].forEach(([label, position]) => { const button = el("button", "secondary small", label); button.type = "button"; button.disabled = position === null; button.addEventListener("click", async () => { await Api.patch(`/api/v1/stores/${layout.id}/sections/${section.id}`, { name: section.name, position }); await this.loadLayout(layout.id); }); row.appendChild(button); });
            const remove = el("button", "secondary small", "×"); remove.type = "button"; remove.addEventListener("click", async () => { await Api.delete(`/api/v1/stores/${layout.id}/sections/${section.id}`); await this.loadLayout(layout.id); }); row.appendChild(remove);
            list.appendChild(row);
        });
        const ingredientSelect = document.getElementById("placement-ingredient");
        const sectionSelect = document.getElementById("placement-section");
        if (ingredientSelect) { ingredientSelect.replaceChildren(); this.state.ingredients.forEach(i => { const o = el("option", null, i.name); o.value = String(i.id); ingredientSelect.appendChild(o); }); }
        if (sectionSelect) { sectionSelect.replaceChildren(); layout.sections.forEach(s => { const o = el("option", null, s.name); o.value = String(s.id); sectionSelect.appendChild(o); }); }
        const placements = document.getElementById("store-placement-list");
        if (placements) {
            placements.replaceChildren(); placements.appendChild(el("p", "muted", t("shop.placement_help")));
            layout.placements.forEach(placement => {
                const row = el("div", "shop-catalog-row");
                const ingredient = this.state.ingredients.find(i => i.id === placement.ingredient_id);
                const section = layout.sections.find(s => s.id === placement.store_section_id);
                row.appendChild(el("span", null, `${ingredient?.name || placement.ingredient_id} · ${section?.name || "?"}${placement.position != null ? ` · ${placement.position + 1}` : ""}`));
                const remove = el("button", "secondary small", "×"); remove.type = "button"; remove.addEventListener("click", async () => { await Api.delete(`/api/v1/stores/${layout.id}/placements/${placement.id}`); await this.loadLayout(layout.id); }); row.appendChild(remove); placements.appendChild(row);
            });
        }
    },
    async addStore(name) { const response = await Api.post("/api/v1/stores", { name }); this.state.stores.push(await response.json()); this.renderStoreChoices(); },
    async renameStore(name) { if (!this.state.activeStoreId) return; const response = await Api.patch(`/api/v1/stores/${this.state.activeStoreId}`, { name }); const store = await response.json(); const current = this.state.stores.find(item => item.id === store.id); if (current) current.name = store.name; this.renderStoreChoices(); },
    async addSection(name) { if (!this.state.activeStoreId) return; await Api.post(`/api/v1/stores/${this.state.activeStoreId}/sections`, { name }); await this.loadLayout(this.state.activeStoreId); },
    async addPlacement(ingredientId, sectionId, position) {
        if (!this.state.activeStoreId) return;
        await Api.post(`/api/v1/stores/${this.state.activeStoreId}/placements`, { ingredient_id: Number(ingredientId), store_section_id: Number(sectionId), position: position === "" ? null : Number(position) });
        await this.loadLayout(this.state.activeStoreId);
    }
};
const ShopCatalog = StoreLayouts;


const App = {
    init() {
        UI.theme.load();
        Recipes.load({ reset: true });
        const sentinel = document.getElementById("recipes-sentinel");
        if (sentinel && "IntersectionObserver" in window) {
            new IntersectionObserver(entries => {
                if (entries.some(entry => entry.isIntersecting)) Recipes.loadNext();
            }, { rootMargin: "320px 0px" }).observe(sentinel);
        }
        Shopping.render();
        Shopping.updateImportButton();
        StoreLayouts.load();
        document.getElementById("shopping-store-select")?.addEventListener("change", event => StoreLayouts.selectStore(event.target.value));
        document.getElementById("store-layout-select")?.addEventListener("change", event => StoreLayouts.selectStore(event.target.value));
        document.getElementById("open-store-layout-btn")?.addEventListener("click", () => {
            UI.openModal("store-layout-modal"); StoreLayouts.renderStoreChoices(); StoreLayouts.renderEditor();
        });
        document.querySelector("[data-close-store-layout]")?.addEventListener("click", () => UI.closeModal("store-layout-modal"));
        document.getElementById("store-form")?.addEventListener("submit", async event => {
            event.preventDefault();
            const input = document.getElementById("store-name");
            try {
                await StoreLayouts.addStore(input.value);
                input.value = "";
                UI.toast(t("shop.store_saved"));
            } catch (err) {
                UI.toast(t("toast.server_error"), "warn");
            }
        });
        document.getElementById("section-form")?.addEventListener("submit", async event => {
            event.preventDefault();
            const input = document.getElementById("section-name");
            try {
                await StoreLayouts.addSection(input.value);
                input.value = "";
            } catch (err) {
                UI.toast(t("toast.server_error"), "warn");
            }
        });
        document.getElementById("store-rename-form")?.addEventListener("submit", async event => {
            event.preventDefault();
            try { await StoreLayouts.renameStore(document.getElementById("store-rename").value); UI.toast(t("shop.store_saved")); }
            catch (err) { UI.toast(t("toast.server_error"), "warn"); }
        });
        document.getElementById("placement-form")?.addEventListener("submit", async event => {
            event.preventDefault();
            try {
                await StoreLayouts.addPlacement(document.getElementById("placement-ingredient").value, document.getElementById("placement-section").value, document.getElementById("placement-position").value);
                document.getElementById("placement-position").value = "";
            } catch (err) { UI.toast(t("toast.server_error"), "warn"); }
        });
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
                    // Shopping.addItem() nigdy nie istniało - Enter rzucał
                    // TypeError i pozycja nie trafiała na listę, mimo że
                    // przycisk "Add" obok działał.
                    addShoppingItem();
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

        /* Zgodność wstecz: pojedynczy przycisk (jeśli istnieje) cyklicznie
           przełącza motywy. Docelowy wybór motywu robią przyciski
           [data-theme-option] w burger menu. */
        const themeBtn = document.getElementById("theme-toggle");
        if (themeBtn) {
            themeBtn.addEventListener("click", () => UI.theme.toggle());
        }

        document.querySelectorAll("[data-theme-option]").forEach(btn => {
            btn.addEventListener("click", event => {
                // Keep the settings menu open while cycling themes. On mobile
                // the document-level outside-click handler otherwise closes
                // the burger after the first theme selection.
                event.stopPropagation();
                UI.theme.set(btn.dataset.themeOption);
            });
        });

        document.querySelectorAll(".language-options").forEach(form => {
            form.addEventListener("submit", event => {
                const selected = event.submitter?.value;
                if (!selected) return;

                form.querySelectorAll("[name=code]").forEach(btn => {
                    const active = btn.value === selected;
                    btn.classList.toggle("active", active);
                    btn.setAttribute("aria-pressed", String(active));
                    if (active) btn.setAttribute("aria-current", "true");
                    else btn.removeAttribute("aria-current");
                });
            });
        });


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
        UI.toast(t("toast.cannot_change_visibility"));
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
    document.getElementById("delete-text").innerText = t("recipes.delete_modal.confirm_text", { name });
    UI.openModal("delete-modal");
}
function closeDeleteModal() { deleteRecipeId = null; UI.closeModal("delete-modal"); }

async function confirmDeleteYes() {
    if (!deleteRecipeId) return;
    try {
        await Api.delete(`/api/v1/recipes/${deleteRecipeId}`);


        closeDeleteModal();
        closeEdit();
        Recipes.load({ reset: true });
        UI.toast(t("toast.recipe_deleted"), "success");

    } catch (err) { console.error(err); UI.toast(t("toast.server_error"), "warn"); }
}

// === INSTRUCTIONS MODAL ===
function showInstructions(text) {
    const modalText = document.getElementById("modal-text");

    // Łamanie linii budujemy z prawdziwych elementów <br>, a same linie wchodzą
    // jako tekst. Sklejenie ich w string i przypisanie do innerHTML wykonywało
    // znaczniki zapisane w instrukcjach przepisu.
    modalText.replaceChildren();
    const lines = (text ?? "").split("\n").map(line => line.trim());

    lines.forEach((line, index) => {
        if (index > 0) modalText.appendChild(document.createElement("br"));
        modalText.appendChild(document.createTextNode(line));
    });

    UI.openModal("modal");
}

function closeModal() {
    UI.closeModal("modal");

}


let recipeSearchTimer = null;
function filterRecipes() {
    clearTimeout(recipeSearchTimer);
    const query = document.getElementById("search").value;
    recipeSearchTimer = setTimeout(() => Recipes.load({ reset: true, query }), 250);
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
        StoreLayouts.load();
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
        Shopping.state.mode ? t("toast.shopping_mode_on") : t("toast.shopping_mode_off"),
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
        t("shopping.clear_modal.text");

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
    UI.toast(t("toast.selected_added_to_list"));
}

function updateShoppingTitle() {
    const title = document.getElementById("shopping-title");
    if (!title) return;

    title.textContent = Shopping.state.mode
        ? t("shopping.title_mode")
        : t("shopping.title_default");
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
        UI.toast(t("toast.image_update_failed"), "error");
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

        UI.toast(t("toast.image_removed"), "success");
    } catch (err) {
        console.error(err);
        UI.toast(err.message, "error");
    }
}


// openIngredientsModal() usunięte razem z pozycją menu "Ingredients" - jedyne,
// co robiło, to toast "funkcja wkrótce dostępna".


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
        UI.toast(t("toast.paste_list_first"), "warn");
        return;
    }

    const lines = value
        .split("\n")
        .map(line => line.trim())
        .filter(Boolean);

    if (!lines.length) {
        UI.toast(t("toast.nothing_to_import"), "warn");
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

    UI.toast(t("toast.list_imported"), "success");
}

/* =========================
   RECIPE IMPORT FROM URL
   ========================= */

const ImportState = {
    ingredients: [],
    sourceUrl: "",
    sourceName: "",
    sourceAuthor: "",
    imageUrl: "",
    previewToken: "",
    submitting: false
};

function openImportUrlModal() {
    const modal = document.getElementById("import-url-modal");
    if (!modal) return;

    document.getElementById("import-url-input").value = "";
    document.getElementById("import-url-error").style.display = "none";
    document.getElementById("import-url-loading").style.display = "none";
    document.getElementById("analyze-import-url-btn").disabled = false;
    ImportState.previewToken = "";

    modal.classList.add("open");
    document.body.classList.add("modal-open");
}

function closeImportUrlModal() {
    const modal = document.getElementById("import-url-modal");
    if (!modal) return;
    modal.classList.remove("open");
    document.body.classList.remove("modal-open");
}

function showImportUrlError(message) {
    const errorBox = document.getElementById("import-url-error");
    errorBox.textContent = message;
    errorBox.style.display = "block";
}

const IMPORT_ERROR_CODE_KEYS = {
    invalid_url: "import.error.invalid_url",
    blocked_host: "import.error.blocked_host",
    too_many_redirects: "import.error.too_many_redirects",
    timeout: "import.error.timeout",
    too_large: "import.error.too_large",
    unsupported_content_type: "import.error.unsupported_content_type",
    no_recipe_found: "import.error.no_recipe_found",
    upstream_error: "import.error.upstream_error",
    invalid_preview_token: "import.error.invalid_preview_token",
    preview_token_owner_mismatch: "import.error.preview_token_owner_mismatch",
    preview_token_expired: "import.error.preview_token_expired",
    preview_token_source_mismatch: "import.error.preview_token_source_mismatch",
    preview_required: "import.error.preview_required",
    invalid_quantity: "import.error.invalid_quantity",
    payload_invalid: "import.error.payload_invalid",
    network_error: "import.error.network_error",
    api_error: "import.error.api_error",
    recipe_persistence_conflict: "import.error.recipe_persistence_conflict",
    recipe_persistence_failed: "import.error.recipe_persistence_failed",
    import_failed: "import.error.generic"
};

function importErrorMessage(errorCode) {
    const key = IMPORT_ERROR_CODE_KEYS[errorCode] || IMPORT_ERROR_CODE_KEYS.import_failed;
    return t(key);
}

function parseNumberOrNull(value) {
    const normalized = String(value ?? "").trim().replace(",", ".");
    if (!normalized) return null;

    const parsed = Number(normalized);
    if (!Number.isFinite(parsed) || parsed < 0) {
        throw new Error("invalid_quantity");
    }
    return parsed;
}

function importErrorCodeFromError(err) {
    if (err && err.message === "invalid_quantity") return "invalid_quantity";

    try {
        const parsed = JSON.parse(err.message);
        const detail = parsed && parsed.detail;
        if (typeof detail === "object" && detail?.error_code) {
            return detail.error_code;
        }
    } catch (_) {
        // The response was not JSON; use the status/network fallback below.
    }

    if (err?.name === "TypeError") return "network_error";
    if (err?.name === "ApiError") return "api_error";
    return "payload_invalid";
}

async function analyzeImportUrl() {
    const input = document.getElementById("import-url-input");
    const url = input.value.trim();

    document.getElementById("import-url-error").style.display = "none";

    if (!url) {
        showImportUrlError(t("import.error.empty_url"));
        return;
    }

    const analyzeBtn = document.getElementById("analyze-import-url-btn");
    analyzeBtn.disabled = true;
    document.getElementById("import-url-loading").style.display = "flex";

    try {
        const res = await Api.post("/api/v1/recipe-import/preview", { url });
        const draft = await res.json();
        closeImportUrlModal();
        openImportDraftModal(draft);
    } catch (err) {
        let errorCode = "import_failed";
        try {
            const parsed = JSON.parse(err.message);
            const detail = parsed && parsed.detail;
            errorCode = (detail && detail.error_code) || errorCode;
        } catch (_) {
            // err.message wasn't JSON (network-level failure) - fall back to generic.
        }
        showImportUrlError(importErrorMessage(errorCode));
    } finally {
        analyzeBtn.disabled = false;
        document.getElementById("import-url-loading").style.display = "none";
    }
}

function openImportDraftModal(draft) {
    const modal = document.getElementById("import-draft-modal");
    if (!modal) return;

    ImportState.previewToken = draft.preview_token || "";
    ImportState.sourceUrl = draft.source_url || "";
    ImportState.sourceName = draft.source_name || "";
    ImportState.sourceAuthor = draft.source_author || "";
    ImportState.imageUrl = isSafeImportImageUrl(draft.image_url) ? draft.image_url : "";
    ImportState.ingredients = (draft.ingredients || []).map(ing => ({
        original_text: ing.original_text,
        quantity: ing.quantity,
        unit: ing.unit || "",
        name: ing.name,
        note: ing.note || "",
        confidence: ing.confidence,
        requires_review: !!ing.requires_review
    }));

    document.getElementById("import-draft-name").value = draft.name || "";
    document.getElementById("import-draft-description").value = draft.description || "";
    document.getElementById("import-draft-instructions").value = draft.instructions || "";
    document.getElementById("import-draft-is-public").checked = false;
    document.getElementById("import-draft-author").value = draft.source_author || "";

    const downloadImageCheckbox = document.getElementById("import-draft-download-image");
    downloadImageCheckbox.checked = !!ImportState.imageUrl;
    downloadImageCheckbox.disabled = !ImportState.imageUrl;
    renderImportImagePreview();

    renderImportWarnings(draft.warnings || []);
    renderImportSourceChip();
    renderImportIngredientsTable();

    const confirmBtn = document.getElementById("confirm-import-btn");
    confirmBtn.disabled = false;
    confirmBtn.textContent = t("import.save_button");
    ImportState.submitting = false;

    modal.classList.add("open");
    document.body.classList.add("modal-open");
}

function isSafeImportImageUrl(value) {
    if (typeof value !== "string" || !value.trim()) return false;
    try {
        const parsed = new URL(value, window.location.href);
        return parsed.protocol === "http:" || parsed.protocol === "https:";
    } catch (_) {
        return false;
    }
}

function closeImportDraftModal() {
    const modal = document.getElementById("import-draft-modal");
    if (!modal) return;
    modal.classList.remove("open");
    document.body.classList.remove("modal-open");
    ImportState.previewToken = "";
}

function renderImportImagePreview() {
    const row = document.getElementById("import-image-preview-row");
    const img = document.getElementById("import-image-preview");
    if (ImportState.imageUrl) {
        img.src = ImportState.imageUrl;
        row.style.display = "block";
    } else {
        row.style.display = "none";
    }
}

const IMPORT_WARNING_KEYS = {
    no_structured_recipe_data: "import.warning.no_structured_data",
    no_ingredients_found: "import.warning.no_ingredients",
    no_instructions_found: "import.warning.no_instructions",
    no_image_found: "import.warning.no_image",
    some_ingredients_need_review: "import.warning.needs_review",
    image_download_failed: "import.warning.image_download_failed",
    duplicate_import_returned_existing: "import.warning.duplicate"
};

function renderImportWarnings(warningCodes) {
    const box = document.getElementById("import-warnings");
    box.innerHTML = "";

    warningCodes.forEach(code => {
        const key = IMPORT_WARNING_KEYS[code];
        if (!key) return;

        const item = document.createElement("div");
        item.className = "import-warning-item";
        item.textContent = t(key);
        box.appendChild(item);
    });
}

function renderImportSourceChip() {
    const chip = document.getElementById("import-source-chip");
    chip.textContent = ImportState.sourceName
        ? `${t("import.source_label")} ${ImportState.sourceName}`
        : "";
}

function renderImportIngredientsTable() {
    const body = document.getElementById("import-ingredients-body");
    body.innerHTML = "";

    ImportState.ingredients.forEach((item, index) => {
        body.appendChild(buildImportIngredientRow(item, index));
    });
}

function buildImportIngredientRow(item, index) {
    const row = document.createElement("tr");
    row.dataset.index = String(index);

    const originalCell = document.createElement("td");
    originalCell.className = "ing-original-cell";
    originalCell.textContent = item.original_text;
    row.appendChild(originalCell);

    row.appendChild(buildImportIngredientInputCell(index, "quantity", item.quantity ?? ""));
    row.appendChild(buildImportIngredientInputCell(index, "unit", item.unit));
    row.appendChild(buildImportIngredientInputCell(index, "name", item.name));
    row.appendChild(buildImportIngredientInputCell(index, "note", item.note));

    const actionsCell = document.createElement("td");
    if (item.requires_review) {
        const pill = document.createElement("span");
        pill.className = "ing-review-pill review";
        pill.textContent = t("import.needs_review_pill");
        actionsCell.appendChild(pill);
    }
    const removeBtn = document.createElement("button");
    removeBtn.type = "button";
    removeBtn.className = "ing-remove-btn";
    removeBtn.textContent = "✖";
    removeBtn.title = t("import.remove_ingredient_title");
    removeBtn.addEventListener("click", () => removeImportIngredientRow(index));
    actionsCell.appendChild(removeBtn);
    row.appendChild(actionsCell);

    return row;
}

function buildImportIngredientInputCell(index, field, value) {
    const cell = document.createElement("td");
    const input = document.createElement("input");
    input.type = "text";
    input.value = value === null || value === undefined ? "" : String(value);
    input.addEventListener("input", () => {
        ImportState.ingredients[index][field] = input.value;
    });
    cell.appendChild(input);
    return cell;
}

function addImportIngredientRow() {
    ImportState.ingredients.push({
        original_text: "",
        quantity: null,
        unit: "",
        name: "",
        note: "",
        confidence: null,
        requires_review: false
    });
    renderImportIngredientsTable();
}

function removeImportIngredientRow(index) {
    ImportState.ingredients.splice(index, 1);
    renderImportIngredientsTable();
}

function buildImportConfirmPayload() {
    return {
        preview_token: ImportState.previewToken,
        source_url: ImportState.sourceUrl,
        source_name: ImportState.sourceName || null,
        source_author: document.getElementById("import-draft-author").value.trim() || null,
        name: document.getElementById("import-draft-name").value.trim(),
        description: document.getElementById("import-draft-description").value || null,
        instructions: document.getElementById("import-draft-instructions").value || null,
        is_public: document.getElementById("import-draft-is-public").checked,
        image_url: ImportState.imageUrl || null,
        download_image: document.getElementById("import-draft-download-image").checked,
        save_structured_ingredients: document.getElementById("import-save-structured-ingredients").checked,
        ingredients: ImportState.ingredients.map(item => ({
            original_text: item.original_text,
            quantity: parseNumberOrNull(item.quantity),
            unit: item.unit || null,
            name: item.name,
            note: item.note || null,
            confidence: item.confidence,
            requires_review: !!item.requires_review
        }))
    };
}

function validateImportIngredients() {
    for (const item of ImportState.ingredients) {
        if (!String(item.original_text || "").trim() || !String(item.name || "").trim()) {
            UI.toast(t("import.error.ingredient_required"), "warn");
            return false;
        }
    }
    return true;
}

async function confirmImportSave() {
    if (ImportState.submitting) return;

    if (!ImportState.previewToken) {
        UI.toast(t("import.error.preview_required"), "error");
        return;
    }

    const nameInput = document.getElementById("import-draft-name");
    if (!nameInput.value.trim()) {
        UI.toast(t("import.error.title_required"), "warn");
        return;
    }
    if (!validateImportIngredients()) return;

    ImportState.submitting = true;
    const confirmBtn = document.getElementById("confirm-import-btn");
    confirmBtn.disabled = true;
    confirmBtn.textContent = t("import.saving");

    try {
        let payload;
        try {
            payload = buildImportConfirmPayload();
        } catch (err) {
            UI.toast(importErrorMessage(importErrorCodeFromError(err)), "error");
            return;
        }
        const res = await Api.post("/api/v1/recipe-import/confirm", payload);
        const data = await res.json();

        closeImportDraftModal();
        await Recipes.load({ reset: true });

        if (data.warnings && data.warnings.includes("image_download_failed")) {
            UI.toast(t("import.warning.image_download_failed"), "warn");
        } else {
            UI.toast(t("import.success"), "success");
        }
    } catch (err) {
        const errorCode = importErrorCodeFromError(err);
        if (errorCode.startsWith("preview_token_") || errorCode === "invalid_preview_token") {
            ImportState.previewToken = "";
        }
        UI.toast(importErrorMessage(errorCode), "error");
    } finally {
        ImportState.submitting = false;
        confirmBtn.disabled = false;
        confirmBtn.textContent = t("import.save_button");
    }
}

const openImportUrlBtn = document.getElementById("open-import-url-btn");
if (openImportUrlBtn) openImportUrlBtn.addEventListener("click", openImportUrlModal);

const closeImportUrlBtn = document.getElementById("close-import-url-modal");
if (closeImportUrlBtn) closeImportUrlBtn.addEventListener("click", closeImportUrlModal);

const cancelImportUrlBtn = document.getElementById("cancel-import-url-btn");
if (cancelImportUrlBtn) cancelImportUrlBtn.addEventListener("click", closeImportUrlModal);

const analyzeImportUrlBtn = document.getElementById("analyze-import-url-btn");
if (analyzeImportUrlBtn) analyzeImportUrlBtn.addEventListener("click", analyzeImportUrl);

const closeImportDraftBtn = document.getElementById("close-import-draft-modal");
if (closeImportDraftBtn) closeImportDraftBtn.addEventListener("click", closeImportDraftModal);

const cancelImportDraftBtn = document.getElementById("cancel-import-draft-btn");
if (cancelImportDraftBtn) cancelImportDraftBtn.addEventListener("click", closeImportDraftModal);

const importAddIngredientBtn = document.getElementById("import-add-ingredient-btn");
if (importAddIngredientBtn) importAddIngredientBtn.addEventListener("click", addImportIngredientRow);

const confirmImportBtn = document.getElementById("confirm-import-btn");
if (confirmImportBtn) confirmImportBtn.addEventListener("click", confirmImportSave);
