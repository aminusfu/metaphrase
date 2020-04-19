//                                 UTILITIES                                 //

function commafy(text) {
    return text.toString().replace(/\d(?=(?:\d\d\d)+(?!\d))/g, "$&,");
}

function truncate(text, len) {
    if (text.length > len) text = text.substring(0, len - 3) + '...';
    return text;
}

function ISODate(d) {
    var dy = d.getFullYear();
    // Y2K
    if (dy < 1970) dy = dy + 100;
    var dm = (d.getMonth() + 1).toString();
    if (dm.length < 2) dm = "0" + dm;
    var dd = d.getDate().toString();
    if (dd.length < 2) dd = "0" + dd;
    return dy + "-" + dm + "-" + dd;
}

function date_from_iso(d) {
    var y = parseInt(d.substring(0, 4), 10);
    var m = parseInt(d.substring(5, 7), 10) - 1;
    var dy = parseInt(d.substring(8, 10), 10);
    return new Date(y, m, dy);
}

function keys(obj) {
    // Return an array of the keys of the given object.
   var k = [];
   for (var key in obj){
      k.push(key);
   }
   return k;
}

function sort(arr) {
    // Sort the given array in place and return it.
    arr.sort();
    return arr;
}

function fromkeys(arr, value) {
    // Return an object formed from the given array as keys
    if (value === undefined) value = 0;

    var obj = {};
    for (var i=0; i < arr.length; i++) {
        obj[arr[i]] = value;
    }
    return obj;
}

function associate(keys, arr) {
    // Return an object with the given keys associated with elements from the given array.
    var d = {};
    for (var i=0; i < keys.length; i++) {
        d[keys[i]] = arr[i];
    }
    return d;
}

function segment(str, index, separator) {
    // Return the indexed segment of the given string.
    if (typeof(separator) == 'undefined') separator = '/';
    var a = str.split(separator);
    if (index < 0) index = a.length + index;
    return a[index];
}

//                                    DOM                                    //

function $(name) { return document.getElementById(name); }

function cancelBubble(e) {
    var evt = e ? e : window.event;
    if (evt.stopPropagation) evt.stopPropagation();
    if (evt.cancelBubble !== null) evt.cancelBubble = true;
}

function queryParams(qs) {
    // Return an object containing the params found in the given querystring.
    // If qs is not supplied, the current window.location.search is used.
    if (qs === undefined) qs = window.location.search.substr(1);

    var result = {};
    pairs = qs.split('&');
    for (var i = 0; i < pairs.length; i++) {
        var p = pairs[i].split('=');
        if (p.length != 2) continue;
        result[p[0]] = decodeURIComponent(p[1].replace(/\+/g, " "));
    }
    return result;
}

function to_qs(qParams) {
    var qs = [];
    for (var k in qParams) {
        qs.push([k, qParams[k]].join("="));
    }
    qs = qs.join("&");
    if (qs !== "") qs = "?" + qs;
    return qs;
}

function get_text(elem) {
    return (elem.innerText !== undefined) ? elem.innerText : elem.textContent;
}

function set_text(elem, newvalue) {
    if (elem.innerText !== undefined) {
        // Internet Explorer
        elem.innerText = newvalue;
    } else {
        // Mozilla
        elem.textContent = newvalue;
    }
}

function selopt(select_element) {
    // Return select element's selected option.
    return select_element.options[select_element.selectedIndex];
}

function option_text(options, value) {
    // Return .text from the option whose .value matches the given value,
    // otherwise return the original value
    for (var i = 0; i < options.length; i++) {
        if (options[i].value == value) {
            return options[i].text;
        }
    }
    return value;
}

function set_option(select_element, value) {
    // Set the .selectedIndex to that of the given value.
    var options = select_element.options;
    for (var i=0; i < options.length; i++) {
        if (options[i].value == value) {
            select_element.selectedIndex = i;
            return true;
        }
    }
    return false;
}

function http(method, url, async, msg) {
    var h;

    if (typeof(XMLHttpRequest) != "undefined") {
        h = new XMLHttpRequest();
    } else {
        try { h = new ActiveXObject("Msxml2.XMLHTTP"); }
        catch (e) {
            try { h = new ActiveXObject("Microsoft.XMLHTTP"); }
            catch (E) { set_status("Your browser is not supported.", 5000, "#660000"); }
        }
    }

    if (msg !== undefined) var m = set_status(msg);

    h.onreadystatechange = function() {
        if (h.readyState == 4) {
            var status = null;
            try {
                status = h.status;
            } catch(e) {
                status = "NO HTTP RESPONSE";
            }

            if (status in h) {
                // Use a custom handler (defined on the XMLHttpRequest object
                //  itself by the caller of this function).
                h[status](h);
            } else {
                // Use a default handler.
                var v = h.status.toString() + ' ' + h.statusText;
                if (status >= 500) {
                    var ct = h.getResponseHeader("Content-Type");
                    var is_html = (ct && ct.indexOf("html") != -1);
                    set_fatal("Failure (" + v + "): " + (msg ? msg : url),
                              h.responseText, is_html);
                } else {
                    set_status("Failure (" + v + "): " + (msg ? msg : url),
                               5000, "#660000");
                }
            }

            if (msg !== undefined) remove_status(m);
        }
    };

    h.open(method, url, async);
    return h;
}

function fadeIn(element, msecs) {
    var op = 0.0;
    element.style.display = 'block';
    var timer = setInterval(function () {
        if (op >= 1) clearInterval(timer);
        element.style.opacity = op;
        op += 1 / (msecs / 20);
    }, 20);
}

function fadeOut(element, msecs) {
    var op = 1.0;
    var timer = setInterval(function () {
        if (op <= 0) {
            clearInterval(timer);
            element.style.display = 'none';
        }
        element.style.opacity = op;
        op -= 1 / (msecs / 20);
    }, 20);
}

passage_font_size = 16;

function biggerBench() {
    passage_font_size += 2;
    workbench.style.fontSize = passage_font_size + "pt";
}

function smallerBench() {
    passage_font_size -= 2;
    if (passage_font_size < 2) passage_font_size = 2;
    workbench.style.fontSize = passage_font_size + "pt";
}

//                                   STATUS                                   //

function set_fatal(title, msg, is_html) {
    set_text($("fatal_error_title"), title);
    if (is_html) {
        $("fatal_error_msg").innerHTML = msg;
    } else {
        set_text($("fatal_error_msg"), msg);
    }
    $("fatal_error").style.zIndex = 100;
    $("fatal_error").style.visibility = 'visible';
}

function remove_fatal() {
    set_text($("fatal_error_title"), "");
    $("fatal_error_msg").innerHTML = "";
    $("fatal_error").style.visibility = 'hidden';
    $("fatal_error").style.zIndex = -1;
}

function set_status(msg, decay, color) {
    var log = $("status");
    var m = document.createElement("p");
    if (color !== undefined) m.style.backgroundColor = color;
    set_text(m, msg);
    log.appendChild(m);
    if (decay !== undefined) {
        setTimeout(function () { remove_status(m); }, decay);
    }
    return m;
}

function remove_status(msgelem) {
    if (msgelem.parentNode) msgelem.parentNode.removeChild(msgelem);
}

//                                   COLLATION                                   //

function reverse_map_of_arrays(obj, rev) {
    // Reverse the given {k1: [v1, v2, ...]} map to be
    // of the form {v1: k1, v2: k1, ...}
    if (rev === undefined) rev = {};
    for (var k in obj) {
        var v = obj[k];
        for (var r=0; r < v.length; r++) {
            rev[v[r]] = k;
        }
    }
    return rev;
}

function Collation(map) {
    var self = reverse_map_of_arrays(map);

    self.collatable = function (s) {
        // Normalize the given string (removing accents, etc)
        for (var c in self) {
            s = s.replace(c, self[c]);
        }
        return s;
    };

    self.collate = function (a, b) {
        // Comparison function for collatable strings.
        a = self.collatable(a);
        b = self.collatable(b);
        if (a < b) return -1;
        if (a > b) return 1;
        return 0;
    };

    return self;
}


//                                   LOG IN                                   //


function login_success(h) {
    // Do nothing by default. Each page that loads this module
    // should override this function if they want to respond
    // to login success.
}

function login_pass() {
    var h = http("POST", "/api/login/", true, "Verifying...");
    h[200] = h[204] = login_success;
    h.setRequestHeader("Content-Type", "application/json");
    h.send(JSON.stringify({
        "email": $('email').value,
        "password": $('password').value
    }));
}

function get_cookies() {
    // Return document.cookies as a dict.
    var cookies = {};
    var atoms = document.cookie.split(';');
    for(var i=0; i < atoms.length; i++) {
        var pair = atoms[i].split("=");
        var k = pair.shift().trim();
        var v = pair.join("=").trim();
        if (v.charAt(0) === '"' && v.charAt(v.length - 1) === '"') v = v.substr(1, v.length - 2);
        cookies[k] = v;
    }
    return cookies;
}

//                                   NoteBox                                   //

function NoteBox(id, classname, contents, writer) {
    // Return a <p> element with editableness.
    var box = document.createElement("p");
    box.id = id;
    box.className = "note_box " + classname;
    box.contentEditable = "false";
    box.contents = contents;
    set_text(box, contents);

    if (writer) {
        box.onclick = function () {
            if (box.contentEditable == "false") {
                box.contentEditable = "true";
            } else {
                box.contentEditable = "false";

                box.contents = get_text(box);
            }
            box.classList.toggle("note_box_editable");
        };
    }

    return box;
}
