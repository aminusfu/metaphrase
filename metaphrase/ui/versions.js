// Requires:
// <script type="text/javascript" src="/ui/json2.js"></script>
// <script type="text/javascript" src="/ui/common.js"></script>

// Depends on the following global variables in some other script:
// var api_root = "/api/";

var params = queryParams();

var versions = params['versions'];
versions = (versions === undefined || versions === null) ? [] : versions.split(",");

var context = params['context'];
if (context === undefined || context === "") context = "6";


function fill_versions(sel, versions) {
    // Populate the given <select> element with options for each version
    for (var v=0; v < versions.length; v++) {
        var option = document.createElement("option");
        option.text = versions[v];
        option.value = versions[v];
        sel.appendChild(option);
    }
    return sel;
}

// --------------------------- Version header --------------------------- //

function fill_version_header() {
    // Set the innerHTML of the versions_header div to the currently-selected versions
    var markers = [];
    for (var v = 0; v < versions.length; v++) {
        markers.push("<span class='version_marker' id='version_marker_" + versions[v] + "'>" + versions[v] + "</span>");
    }
    $('versions_header').innerHTML = markers.join(',&nbsp;') || "Click to select versions";
}

function set_selected_version(version) {
    selected_version = version;
    var markers = $("versions_header").getElementsByClassName("version_marker");
    for (var i=0; i < markers.length; i++) {
        if (markers[i].id == "version_marker_" + version) {
            markers[i].style.borderBottom = "1px solid white";
        } else {
            markers[i].style.borderBottom = "none";
        }
    }
}

// --------------------------- Version selection --------------------------- //

function toggle_select_versions() {
    var d = $('version_tab');
    if (d.style.display == "block") {
        fadeOut(d, 500);
    } else {
        populate_versions();

        var cookies = get_cookies();
        if (cookies.token === undefined) {
            $('loginform').style.display = 'block';
            try {
                $('email').value = atob(cookies.login);
            } catch(e) {}
        } else {
            $('loginform').style.display = 'none';
        }

        fadeIn(d, 500);
    }
}

version_catalog = undefined;
writable_versions = [];

function populate_versions() {
    // GET the versions/ catalog and populate the "versions" div
    var h = http("GET", api_root + "versions/", true);
    h[200] = function(h) {
        version_catalog = JSON.parse(h.responseText);

        available_versions = {};
        for (var version_url in version_catalog.index) {
            available_versions[segment(version_url, -2)] = version_catalog.index[version_url];
        }

        writable_versions = [];
        for (var a_version in available_versions) {
            var auth = available_versions[a_version]["auth"];
            if (auth["permissions"] !== null) {
                var role = auth["permissions"][version_catalog.username];
                if (role == 'writer' || role == 'admin') writable_versions.push(a_version);
            }
        }

        var vs = $("versions");
        vs.innerHTML = "";

        var seen = [];

        // Add existing selections
        for (var i=0; i < versions.length; i++) {
            var version = versions[i];
            var avail_version = available_versions[version];
            if (avail_version === undefined) continue;

            var bar = make_version_bar(version, "version_label selected_version",
                                       avail_version["auth"], avail_version["notes"]);
            vs.appendChild(bar);
            seen.push(version);
        }

        // Add available selections
        for (var av_version in available_versions) {
            if (seen.indexOf(av_version) != -1) continue;

            var av = available_versions[av_version];

            var av_bar = make_version_bar(av_version, "version_label", av["auth"], av["notes"]);
            vs.appendChild(av_bar);
        }
    };
    h.send();
}

function check_radio(form, name, value) {
    for (var i=0; i < form.elements.length; i++) {
        if(form.elements[i].value == value) {
            form.elements[i].checked = true;
        }
    }
}

function make_version_bar(version_name, labelclassName, auth, version_notes) {
    var perms = auth["permissions"];
    var myrole = perms[version_catalog.username];

    var bar = document.createElement("div");
    bar.className = "version";

    var header = document.createElement("div");
    header.className = "version_header";
    bar.appendChild(header);

    var handle = document.createElement("div");
    handle.className = "version_handle";
        var upbutt = document.createElement("span");
        upbutt.onclick = move_version_up;
        upbutt.innerHTML = "&#9650;";
        handle.appendChild(upbutt);

        handle.appendChild(document.createElement("br"));

        var downbutt = document.createElement("span");
        downbutt.onclick = move_version_down;
        downbutt.innerHTML = "&#9660;";
        handle.appendChild(downbutt);
    header.appendChild(handle);

    var label_div = document.createElement("div");
    label_div.className = labelclassName;
    set_text(label_div, version_name);
    label_div.onclick = version_label_click;
    header.appendChild(label_div);

    // Show an extra pane with copying options
    var copy_div = document.createElement("div");
    copy_div.className = "copy_div";
    copy_div.style.display = "none";
    copy_div.id = "copy_div_" + version_name;

    var selHTML = "";
    var thisSectionButton = "";
    try {
        if (section !== undefined) {
            thisSectionButton = "<input type='radio' name='copy_scope' value='section' checked='checked' />&nbsp;This section<br />";
        }
    } catch(e) {}
    var this_version_in_writable_versions = (writable_versions.indexOf(version_name) == -1) ? 0 : 1;
    if (writable_versions.length > this_version_in_writable_versions) {
        for (var i=0; i < writable_versions.length; i++) {
            if (writable_versions[i] != version_name) {
                selHTML += "<option>" + writable_versions[i] + "</option>";
            }
        }
        selHTML =
            "<input type='radio' name='copy_to_new' value='n' checked='checked' />&nbsp;To version<br />" +
            "<select name='copy_to_version' class='mph_select' size='" +
            (writable_versions.length - this_version_in_writable_versions) +
            "' onFocus='check_radio(this.form, \"copy_to_new\", \"n\")'>" + selHTML + "</select><br />";
    }
    copy_div.innerHTML =
        "<form class='copy_form' id='copy_form-" + version_name + "' style='text-align: left'>" +
        "<table><tr><td>" +
        thisSectionButton +
        "<input type='radio' name='copy_scope' value='all' />&nbsp;All sections in this version<br />" +
        "<input type='checkbox' name='copy_translate' />&nbsp;Translate" +
        "</td>" +
        "<td>" + selHTML +
        "<input type='radio' name='copy_to_new' value='y' />&nbsp;New:&nbsp;" +
        "<input type='text' name='copy_new_version' class='mph_select' " +
        "onFocus='check_radio(this.form, \"copy_to_new\", \"y\")' /><br />" +
        "<input type='button' class='copy_submit_button' onclick='copy_click(this.form)' value='SUBMIT' />" +
        "</td></tr></table>" +
        "</form>";
    bar.appendChild(copy_div);

    // Add a button to show/hide the copy pane
    var copy_toggle_button = document.createElement("div");
    copy_toggle_button.className = "copy_toggle_button";
    set_text(copy_toggle_button, "Copy");
    copy_toggle_button.onclick = function () {
        if (copy_div.style.display == "block") {
            fadeOut(copy_div, 500);
        } else {
            fadeIn(copy_div, 500);
        }
    };
    header.appendChild(copy_toggle_button);

    // Show an extra pane with version notes
    var vnote_div = document.createElement("div");
    vnote_div.className = "vnote_div";
    vnote_div.style.display = "none";
    vnote_div.id = "vnote_div_" + version_name;

    var vnote_render = NoteBox(
        'vnote_render_' + version_name, "vnote_render",
        version_notes,
        (myrole == 'writer' || myrole == 'admin')
    );
    vnote_div.appendChild(vnote_render);

    var vnote_save = document.createElement("span");
    vnote_save.className = "vnote_save";
    vnote_save.title = "Save these notes for this version.";
    vnote_save.onclick = function () {
        var vindex = {};
        vindex[version_name + "/"] = {"notes": vnote_render.contents};
        var url = api_root + "versions/";
        var h = http("PATCH", url, true, "Updating version notes...");
        h[204] = function(h) {};
        h.setRequestHeader("Content-Type", "application/json");
        h.send(JSON.stringify({
            "element": "shoji:catalog",
            "index": vindex
        }));
    };
    set_text(vnote_save, "Save");
    vnote_div.appendChild(vnote_save);

    bar.appendChild(vnote_div);

    // Add a button to show/hide the version notes pane
    var vnote_toggle_button = document.createElement("div");
    vnote_toggle_button.className = "vnote_toggle_button";
    vnote_toggle_button.innerHTML = "&#8224;";
    vnote_toggle_button.onclick = function () {
        if (vnote_div.style.display == "block") {
            fadeOut(vnote_div, 500);
        } else {
            fadeIn(vnote_div, 500);
        }
    };
    header.appendChild(vnote_toggle_button);

    // Show a 'Locked' button
    if (myrole == 'writer' || myrole == 'admin') {
        var lock_div = document.createElement("div");
        lock_div.className = "lock_button";
        set_text(lock_div, auth["locked"] ? "Locked" : "Unlocked");
        if (myrole == "admin") {
            lock_div.onclick = version_lock_click;
        }
        lock_div.version_name = version_name;
        header.appendChild(lock_div);
    }

    if (myrole == 'admin') {
        // Show an extra pane with permissions per user
        var auth_div = document.createElement("div");
        auth_div.className = "auth_div";
        auth_div.style.display = "none";
        auth_div.id = "auth_div_" + version_name;
        var auth_table = document.createElement("table");
        auth_table.className = "auth_table";

        // Add rows for existing users
        var users = sort(keys(perms));
        for (var i=0; i < users.length; i++) {
            auth_table.appendChild(
                user_row(version_name, users[i], perms[users[i]])
            );
        }

        // Add a row for adding a user
        // Return a TR element containing auth controls for the given user.
        var row = document.createElement("tr");

        // Add a TD with a '+' button to add a new user.
        var t = document.createElement("td");
        var r = document.createElement("span");
        r.className = "auth_new";
        set_text(r, "+");
        r.version_name = version_name;
        r.onclick = new_user_auth;
        t.appendChild(r);
        row.appendChild(t);

        // Add a spacer TD.
        var t = document.createElement("td");
        t.className = "user";
        row.appendChild(t);

        // Add a spacer TD.
        var t = document.createElement("td");
        t.className = "role";
        row.appendChild(t);

        auth_table.appendChild(row);

        auth_div.appendChild(auth_table);
        bar.appendChild(auth_div);

        // Add a button to show/hide the auth pane
        var auth_toggle_button = document.createElement("div");
        auth_toggle_button.className = "auth_toggle_button";
        set_text(auth_toggle_button, "Auth");
        auth_toggle_button.onclick = function () {
            if (auth_div.style.display == "block") {
                fadeOut(auth_div, 500);
            } else {
                fadeIn(auth_div, 500);
            }
        };
        header.appendChild(auth_toggle_button);
    }

    return bar;
}


function move_version_up(e) {
    var version_bar = e.target.parentNode.parentNode.parentNode;
    console.log(version_bar);
    var all_versions = $("versions");
    var vernodes = all_versions.getElementsByClassName("version");
    for (var i=0; i < vernodes.length; i++) {
        var vernode = vernodes[i];
        console.log(vernode);
        if (vernode === version_bar) {
            if (i > 0) {
                // Move the dragged element
                all_versions.removeChild(version_bar);
                all_versions.insertBefore(version_bar, vernodes[i - 1]);
            }
            break;
        }
    }
}


function move_version_down(e) {
    var version_bar = e.target.parentNode.parentNode.parentNode;
    var all_versions = $("versions");
    var vernodes = all_versions.getElementsByClassName("version");
    for (var i=0; i < vernodes.length; i++) {
        var vernode = vernodes[i];
        if (vernode === version_bar) {
            if (i < (vernodes.length - 1)) {
                // Move the dragged element
                all_versions.removeChild(version_bar);
                all_versions.insertBefore(version_bar, vernodes[i + 1]);
            }
            break;
        }
    }
}


function new_version() {
    var vname = window.prompt("Enter a name for the new version:");
    if (vname === null) return;
    var vindex = {};
    vindex[vname + "/"] = {"auth": {"permissions": {}, "locked": False}};

    var url = api_root + "versions/";
    var h = http("PATCH", url, true, "Creating new version...");
    h[204] = function(h) {
        window.location.reload();
    };
    h.setRequestHeader("Content-Type", "application/json");
    h.send(JSON.stringify({
        "element": "shoji:catalog",
        "index": vindex
    }));
}

function version_label_click() {
    this.classList.toggle("selected_version");
}

function get_version_key(version_name) {
    // Return the full key in version_catalog.index for the given name, or null
    for (var k in version_catalog.index) {
        if (segment(k, -2) == version_name) {
            return k;
        }
    }
    return null;
}

function version_is_locked(version_name) {
    var key = get_version_key(version_name);
    if (key === null) return true;
    return version_catalog.index[key]["auth"]["locked"];
}

function version_lock_click() {
    // Make a copy of the entry for mutation
    var self = this;
    var key = get_version_key(this.version_name);
    if (key === null) return;

    var vauth = JSON.parse(JSON.stringify(version_catalog.index[key]["auth"]));
    vauth["locked"] = !(vauth["locked"]);

    var url = api_root + "versions/";
    var h = http("PATCH", url, true, (vauth["locked"] ? "Locking" : "Unlocking") + " version...");
    h[204] = function(h) {
        // Only update the local copy if the PATCH succeeds.
        version_catalog["index"][key]["auth"]["locked"] = vauth["locked"];
        set_text(self, vauth["locked"] ? "Locked" : "Unlocked");
    };
    h.setRequestHeader("Content-Type", "application/json");
    var index = {};
    index[key] = {"auth": vauth};
    h.send(JSON.stringify({
        "element": "shoji:catalog",
        "index": index
    }));
}

function copy_sections(from_version, to_version, this_section_only, translate) {
    var body = {};
    body["parent"] = from_version;
    if (this_section_only) {
        // Copy this section only
        body["works"] = {};
        body["works"][work + "/"] = {"sections": [section]};
    }
    body["translate"] = translate;

    var url = api_root + "versions/" + to_version + "/";
    var h = http("POST", url, true, "Copying...");
    h[204] = function(h) {};
    h.setRequestHeader("Content-Type", "application/json");
    h.send(JSON.stringify({
        "element": "shoji:entity",
        "body": body
    }));
}

function copy_click(form) {
    // Handle a click on a copy form
    var from_version = form.id.split("-")[1];
    var to_version = null;
    var use_existing = form.elements['copy_to_new'][0].checked;
    if (use_existing) {
        // Use an existing version
        to_version = form.elements['copy_to_version'].options[form.elements['copy_to_version'].selectedIndex].value;
        copy_sections(
            from_version, to_version,
            form.elements['copy_scope'][0].checked,
            form.elements['copy_translate'].checked
        );
    } else {
        // Make a new version
        to_version = form.elements['copy_new_version'].value;

        // Make the requesting user the only admin.
        var index = {};
        var perms = {};
        perms[version_catalog.username] = "admin";
        index[to_version + "/"] = {"auth": {"permissions": perms}};

        var url = api_root + "versions/";
        var h = http("PATCH", url, true, "Creating new version...");
        h[204] = function(h) {
            var bar = make_version_bar(to_version, "version_label", {"permissions": perms}, "");
            $("versions").appendChild(bar);

            copy_sections(
                from_version, to_version,
                form.elements['copy_scope'][0].checked,
                form.elements['copy_translate'].checked
            );
        };
        h.setRequestHeader("Content-Type", "application/json");
        h.send(JSON.stringify({
            "element": "shoji:catalog",
            "index": index
        }));
    }
}

function reload_with_new_versions() {
    var href = window.location.href;

    var selected_versions = [];
    var vnodes = $("versions").getElementsByClassName("selected_version");
    for (var i=0; i < vnodes.length; i++) {
        selected_versions.push(get_text(vnodes[i]));
    }
    params["versions"] = selected_versions.join(",");

    window.location.href = to_qs(params);
}

// --------------------------------- AUTH --------------------------------- //

function user_row(target, user, user_role) {
    // Return a TR element containing auth controls for the given user.
    var row = document.createElement("tr");

    // Add a TD with an 'x' button to remove the user from auth completely.
    var t = document.createElement("td");
    if (version_catalog.username != user) {
        var r = document.createElement("span");
        r.className = "auth_remove";
        set_text(r, "x");
        r.username = user;
        r.target = target;
        r.onclick = remove_user_auth;
        t.appendChild(r);
    }
    row.appendChild(t);

    // Add a TD with the name of the user.
    var t = document.createElement("td");
    t.className = "user";
    set_text(t, user);
    row.appendChild(t);

    // Add a TD with buttons for each available role.
    var t = document.createElement("td");
    t.className = "role";
    // But don't allow admins to switch themselves to any other role.
    var self_admin = (user == version_catalog.username && user_role == "admin");
    for (var each_role in {"none": 0, "reader": 0, "writer": 0, "admin": 0}) {
        var r = document.createElement("span");
        if (self_admin) {
            r.classList.add("auth_disabled");
        } else {
            r.classList.add("auth_enabled");
            r.onclick = click_role;
        }
        if (each_role == user_role) r.classList.add("auth_selected");
        set_text(r, each_role);
        r.username = user;
        r.target = target;
        t.appendChild(r);
    }
    row.appendChild(t);

    return row;
}


function click_role() {
    // Bind this to a local so it's available inside h[204]
    var role = this;

    // Make a copy of the catalog for mutation
    var catalog = JSON.parse(JSON.stringify(version_catalog));
    for (var k in catalog.index) {
        if (segment(k, -2) == role.target) {
            catalog.index[k]["auth"]["permissions"][role.username] = get_text(role);
        } else {
            delete catalog.index[k];
        }
    }

    var url = api_root + "versions/";
    var h = http("PATCH", url, true, "Saving...");
    h[204] = function(h) {
        version_catalog = catalog;

        // Mark the proper option as selected
        var all_roles = role.parentNode.childNodes;
        for (var i=0; i < all_roles.length; i++) {
            var role_span = all_roles[i];
            if (role_span === role) {
                role_span.classList.add("auth_selected");
            } else {
                role_span.classList.remove("auth_selected");
            }
        }
    };
    h.setRequestHeader("Content-Type", "application/json");
    h.send(JSON.stringify(catalog));
}


function new_user_auth() {
    // Add a new auth entry. This won't actually PATCH the resource
    // until the user clicks on a role.

    // Obtain the name of the user.
    // TODO: make this a select instead.
    var user = window.prompt("Enter the name of the user (or 'public' for anonymous permissions).");
    if (user === null) return;

    var thisrow = this.parentNode.parentNode;
    var newrow = user_row(this.version_name, user, "");
    thisrow.parentNode.insertBefore(newrow, thisrow);
}


function remove_user_auth() {
    // Remove an auth entry.

    // Bind this to a local so it's available inside h[204]
    var role = this;

    var thisrow = role.parentNode.parentNode;
    thisrow.parentNode.removeChild(thisrow);

    // Make a copy of the catalog for mutation
    var catalog = JSON.parse(JSON.stringify(version_catalog));
    for (var k in catalog.index) {
        if (segment(k, -2) == role.target) {
            delete catalog.index[k]["auth"]["permissions"][role.username];
        } else {
            delete catalog.index[k];
        }
    }

    var url = api_root + "versions/";
    var h = http("PATCH", url, true, "Saving...");
    h[204] = function(h) {
        version_catalog = catalog;
    };
    h.setRequestHeader("Content-Type", "application/json");
    h.send(JSON.stringify(catalog));
}

function login_success(h) {
    // Called when the XmlHttpRequest in login_pass succeeds with 200/204.
    populate_versions();
    fadeOut($("loginform"), 500);
}
