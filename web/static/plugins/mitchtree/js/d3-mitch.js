(function webpackUniversalModuleDefinition(root, factory) {
	if(typeof exports === 'object' && typeof module === 'object')
		module.exports = factory();
	else if(typeof define === 'function' && define.amd)
		define("mitchTree", [], factory);
	else if(typeof exports === 'object')
		exports["mitchTree"] = factory();
	else
		root["d3"] = root["d3"] || {}, root["d3"]["mitchTree"] = factory();
})(this, function() {
return /******/ (function(modules) { // webpackBootstrap
/******/ 	// The module cache
/******/ 	var installedModules = {};
/******/
/******/ 	// The require function
/******/ 	function __webpack_require__(moduleId) {
/******/
/******/ 		// Check if module is in cache
/******/ 		if(installedModules[moduleId]) {
/******/ 			return installedModules[moduleId].exports;
/******/ 		}
/******/ 		// Create a new module (and put it into the cache)
/******/ 		var module = installedModules[moduleId] = {
/******/ 			i: moduleId,
/******/ 			l: false,
/******/ 			exports: {}
/******/ 		};
/******/
/******/ 		// Execute the module function
/******/ 		modules[moduleId].call(module.exports, module, module.exports, __webpack_require__);
/******/
/******/ 		// Flag the module as loaded
/******/ 		module.l = true;
/******/
/******/ 		// Return the exports of the module
/******/ 		return module.exports;
/******/ 	}
/******/
/******/
/******/ 	// expose the modules object (__webpack_modules__)
/******/ 	__webpack_require__.m = modules;
/******/
/******/ 	// expose the module cache
/******/ 	__webpack_require__.c = installedModules;
/******/
/******/ 	// define getter function for harmony exports
/******/ 	__webpack_require__.d = function(exports, name, getter) {
/******/ 		if(!__webpack_require__.o(exports, name)) {
/******/ 			Object.defineProperty(exports, name, { enumerable: true, get: getter });
/******/ 		}
/******/ 	};
/******/
/******/ 	// define __esModule on exports
/******/ 	__webpack_require__.r = function(exports) {
/******/ 		if(typeof Symbol !== 'undefined' && Symbol.toStringTag) {
/******/ 			Object.defineProperty(exports, Symbol.toStringTag, { value: 'Module' });
/******/ 		}
/******/ 		Object.defineProperty(exports, '__esModule', { value: true });
/******/ 	};
/******/
/******/ 	// create a fake namespace object
/******/ 	// mode & 1: value is a module id, require it
/******/ 	// mode & 2: merge all properties of value into the ns
/******/ 	// mode & 4: return value when already ns object
/******/ 	// mode & 8|1: behave like require
/******/ 	__webpack_require__.t = function(value, mode) {
/******/ 		if(mode & 1) value = __webpack_require__(value);
/******/ 		if(mode & 8) return value;
/******/ 		if((mode & 4) && typeof value === 'object' && value && value.__esModule) return value;
/******/ 		var ns = Object.create(null);
/******/ 		__webpack_require__.r(ns);
/******/ 		Object.defineProperty(ns, 'default', { enumerable: true, value: value });
/******/ 		if(mode & 2 && typeof value != 'string') for(var key in value) __webpack_require__.d(ns, key, function(key) { return value[key]; }.bind(null, key));
/******/ 		return ns;
/******/ 	};
/******/
/******/ 	// getDefaultExport function for compatibility with non-harmony modules
/******/ 	__webpack_require__.n = function(module) {
/******/ 		var getter = module && module.__esModule ?
/******/ 			function getDefault() { return module['default']; } :
/******/ 			function getModuleExports() { return module; };
/******/ 		__webpack_require__.d(getter, 'a', getter);
/******/ 		return getter;
/******/ 	};
/******/
/******/ 	// Object.prototype.hasOwnProperty.call
/******/ 	__webpack_require__.o = function(object, property) { return Object.prototype.hasOwnProperty.call(object, property); };
/******/
/******/ 	// __webpack_public_path__
/******/ 	__webpack_require__.p = "./dist";
/******/
/******/
/******/ 	// Load entry module and return exports
/******/ 	return __webpack_require__(__webpack_require__.s = 0);
/******/ })
/************************************************************************/
/******/ ([
/* 0 */
/***/ (function(module, __webpack_exports__, __webpack_require__) {

"use strict";
__webpack_require__.r(__webpack_exports__);
var d3_hierarchy_src_namespaceObject = {};
__webpack_require__.r(d3_hierarchy_src_namespaceObject);
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "cluster", function() { return cluster; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "hierarchy", function() { return hierarchy; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "pack", function() { return src_pack; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "packSiblings", function() { return siblings; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "packEnclose", function() { return enclose; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "partition", function() { return src_partition; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "stratify", function() { return src_stratify; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "tree", function() { return tree; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "treemap", function() { return src_treemap; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "treemapBinary", function() { return binary; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "treemapDice", function() { return dice; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "treemapSlice", function() { return treemap_slice; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "treemapSliceDice", function() { return sliceDice; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "treemapSquarify", function() { return squarify; });
__webpack_require__.d(d3_hierarchy_src_namespaceObject, "treemapResquarify", function() { return treemap_resquarify; });
var d3_zoom_src_namespaceObject = {};
__webpack_require__.r(d3_zoom_src_namespaceObject);
__webpack_require__.d(d3_zoom_src_namespaceObject, "zoom", function() { return d3_zoom_src_zoom; });
__webpack_require__.d(d3_zoom_src_namespaceObject, "zoomTransform", function() { return transform_transform; });
__webpack_require__.d(d3_zoom_src_namespaceObject, "zoomIdentity", function() { return transform_identity; });

// CONCATENATED MODULE: ./node_modules/d3-selection/src/namespaces.js
var xhtml = "http://www.w3.org/1999/xhtml";

/* harmony default export */ var namespaces = ({
  svg: "http://www.w3.org/2000/svg",
  xhtml: xhtml,
  xlink: "http://www.w3.org/1999/xlink",
  xml: "http://www.w3.org/XML/1998/namespace",
  xmlns: "http://www.w3.org/2000/xmlns/"
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/namespace.js


/* harmony default export */ var namespace = (function(name) {
  var prefix = name += "", i = prefix.indexOf(":");
  if (i >= 0 && (prefix = name.slice(0, i)) !== "xmlns") name = name.slice(i + 1);
  return namespaces.hasOwnProperty(prefix) ? {space: namespaces[prefix], local: name} : name;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/creator.js



function creatorInherit(name) {
  return function() {
    var document = this.ownerDocument,
        uri = this.namespaceURI;
    return uri === xhtml && document.documentElement.namespaceURI === xhtml
        ? document.createElement(name)
        : document.createElementNS(uri, name);
  };
}

function creatorFixed(fullname) {
  return function() {
    return this.ownerDocument.createElementNS(fullname.space, fullname.local);
  };
}

/* harmony default export */ var creator = (function(name) {
  var fullname = namespace(name);
  return (fullname.local
      ? creatorFixed
      : creatorInherit)(fullname);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selector.js
function none() {}

/* harmony default export */ var src_selector = (function(selector) {
  return selector == null ? none : function() {
    return this.querySelector(selector);
  };
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/select.js



/* harmony default export */ var selection_select = (function(select) {
  if (typeof select !== "function") select = src_selector(select);

  for (var groups = this._groups, m = groups.length, subgroups = new Array(m), j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, subgroup = subgroups[j] = new Array(n), node, subnode, i = 0; i < n; ++i) {
      if ((node = group[i]) && (subnode = select.call(node, node.__data__, i, group))) {
        if ("__data__" in node) subnode.__data__ = node.__data__;
        subgroup[i] = subnode;
      }
    }
  }

  return new Selection(subgroups, this._parents);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selectorAll.js
function selectorAll_empty() {
  return [];
}

/* harmony default export */ var selectorAll = (function(selector) {
  return selector == null ? selectorAll_empty : function() {
    return this.querySelectorAll(selector);
  };
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/selectAll.js



/* harmony default export */ var selectAll = (function(select) {
  if (typeof select !== "function") select = selectorAll(select);

  for (var groups = this._groups, m = groups.length, subgroups = [], parents = [], j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, node, i = 0; i < n; ++i) {
      if (node = group[i]) {
        subgroups.push(select.call(node, node.__data__, i, group));
        parents.push(node);
      }
    }
  }

  return new Selection(subgroups, parents);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/matcher.js
/* harmony default export */ var matcher = (function(selector) {
  return function() {
    return this.matches(selector);
  };
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/filter.js



/* harmony default export */ var selection_filter = (function(match) {
  if (typeof match !== "function") match = matcher(match);

  for (var groups = this._groups, m = groups.length, subgroups = new Array(m), j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, subgroup = subgroups[j] = [], node, i = 0; i < n; ++i) {
      if ((node = group[i]) && match.call(node, node.__data__, i, group)) {
        subgroup.push(node);
      }
    }
  }

  return new Selection(subgroups, this._parents);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/sparse.js
/* harmony default export */ var sparse = (function(update) {
  return new Array(update.length);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/enter.js



/* harmony default export */ var selection_enter = (function() {
  return new Selection(this._enter || this._groups.map(sparse), this._parents);
});

function EnterNode(parent, datum) {
  this.ownerDocument = parent.ownerDocument;
  this.namespaceURI = parent.namespaceURI;
  this._next = null;
  this._parent = parent;
  this.__data__ = datum;
}

EnterNode.prototype = {
  constructor: EnterNode,
  appendChild: function(child) { return this._parent.insertBefore(child, this._next); },
  insertBefore: function(child, next) { return this._parent.insertBefore(child, next); },
  querySelector: function(selector) { return this._parent.querySelector(selector); },
  querySelectorAll: function(selector) { return this._parent.querySelectorAll(selector); }
};

// CONCATENATED MODULE: ./node_modules/d3-selection/src/constant.js
/* harmony default export */ var constant = (function(x) {
  return function() {
    return x;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/data.js




var keyPrefix = "$"; // Protect against keys like “__proto__”.

function bindIndex(parent, group, enter, update, exit, data) {
  var i = 0,
      node,
      groupLength = group.length,
      dataLength = data.length;

  // Put any non-null nodes that fit into update.
  // Put any null nodes into enter.
  // Put any remaining data into enter.
  for (; i < dataLength; ++i) {
    if (node = group[i]) {
      node.__data__ = data[i];
      update[i] = node;
    } else {
      enter[i] = new EnterNode(parent, data[i]);
    }
  }

  // Put any non-null nodes that don’t fit into exit.
  for (; i < groupLength; ++i) {
    if (node = group[i]) {
      exit[i] = node;
    }
  }
}

function bindKey(parent, group, enter, update, exit, data, key) {
  var i,
      node,
      nodeByKeyValue = {},
      groupLength = group.length,
      dataLength = data.length,
      keyValues = new Array(groupLength),
      keyValue;

  // Compute the key for each node.
  // If multiple nodes have the same key, the duplicates are added to exit.
  for (i = 0; i < groupLength; ++i) {
    if (node = group[i]) {
      keyValues[i] = keyValue = keyPrefix + key.call(node, node.__data__, i, group);
      if (keyValue in nodeByKeyValue) {
        exit[i] = node;
      } else {
        nodeByKeyValue[keyValue] = node;
      }
    }
  }

  // Compute the key for each datum.
  // If there a node associated with this key, join and add it to update.
  // If there is not (or the key is a duplicate), add it to enter.
  for (i = 0; i < dataLength; ++i) {
    keyValue = keyPrefix + key.call(parent, data[i], i, data);
    if (node = nodeByKeyValue[keyValue]) {
      update[i] = node;
      node.__data__ = data[i];
      nodeByKeyValue[keyValue] = null;
    } else {
      enter[i] = new EnterNode(parent, data[i]);
    }
  }

  // Add any remaining nodes that were not bound to data to exit.
  for (i = 0; i < groupLength; ++i) {
    if ((node = group[i]) && (nodeByKeyValue[keyValues[i]] === node)) {
      exit[i] = node;
    }
  }
}

/* harmony default export */ var selection_data = (function(value, key) {
  if (!value) {
    data = new Array(this.size()), j = -1;
    this.each(function(d) { data[++j] = d; });
    return data;
  }

  var bind = key ? bindKey : bindIndex,
      parents = this._parents,
      groups = this._groups;

  if (typeof value !== "function") value = constant(value);

  for (var m = groups.length, update = new Array(m), enter = new Array(m), exit = new Array(m), j = 0; j < m; ++j) {
    var parent = parents[j],
        group = groups[j],
        groupLength = group.length,
        data = value.call(parent, parent && parent.__data__, j, parents),
        dataLength = data.length,
        enterGroup = enter[j] = new Array(dataLength),
        updateGroup = update[j] = new Array(dataLength),
        exitGroup = exit[j] = new Array(groupLength);

    bind(parent, group, enterGroup, updateGroup, exitGroup, data, key);

    // Now connect the enter nodes to their following update node, such that
    // appendChild can insert the materialized enter node before this node,
    // rather than at the end of the parent node.
    for (var i0 = 0, i1 = 0, previous, next; i0 < dataLength; ++i0) {
      if (previous = enterGroup[i0]) {
        if (i0 >= i1) i1 = i0 + 1;
        while (!(next = updateGroup[i1]) && ++i1 < dataLength);
        previous._next = next || null;
      }
    }
  }

  update = new Selection(update, parents);
  update._enter = enter;
  update._exit = exit;
  return update;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/exit.js



/* harmony default export */ var selection_exit = (function() {
  return new Selection(this._exit || this._groups.map(sparse), this._parents);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/join.js
/* harmony default export */ var join = (function(onenter, onupdate, onexit) {
  var enter = this.enter(), update = this, exit = this.exit();
  enter = typeof onenter === "function" ? onenter(enter) : enter.append(onenter + "");
  if (onupdate != null) update = onupdate(update);
  if (onexit == null) exit.remove(); else onexit(exit);
  return enter && update ? enter.merge(update).order() : update;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/merge.js


/* harmony default export */ var selection_merge = (function(selection) {

  for (var groups0 = this._groups, groups1 = selection._groups, m0 = groups0.length, m1 = groups1.length, m = Math.min(m0, m1), merges = new Array(m0), j = 0; j < m; ++j) {
    for (var group0 = groups0[j], group1 = groups1[j], n = group0.length, merge = merges[j] = new Array(n), node, i = 0; i < n; ++i) {
      if (node = group0[i] || group1[i]) {
        merge[i] = node;
      }
    }
  }

  for (; j < m0; ++j) {
    merges[j] = groups0[j];
  }

  return new Selection(merges, this._parents);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/order.js
/* harmony default export */ var selection_order = (function() {

  for (var groups = this._groups, j = -1, m = groups.length; ++j < m;) {
    for (var group = groups[j], i = group.length - 1, next = group[i], node; --i >= 0;) {
      if (node = group[i]) {
        if (next && node.compareDocumentPosition(next) ^ 4) next.parentNode.insertBefore(node, next);
        next = node;
      }
    }
  }

  return this;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/sort.js


/* harmony default export */ var selection_sort = (function(compare) {
  if (!compare) compare = ascending;

  function compareNode(a, b) {
    return a && b ? compare(a.__data__, b.__data__) : !a - !b;
  }

  for (var groups = this._groups, m = groups.length, sortgroups = new Array(m), j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, sortgroup = sortgroups[j] = new Array(n), node, i = 0; i < n; ++i) {
      if (node = group[i]) {
        sortgroup[i] = node;
      }
    }
    sortgroup.sort(compareNode);
  }

  return new Selection(sortgroups, this._parents).order();
});

function ascending(a, b) {
  return a < b ? -1 : a > b ? 1 : a >= b ? 0 : NaN;
}

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/call.js
/* harmony default export */ var call = (function() {
  var callback = arguments[0];
  arguments[0] = this;
  callback.apply(null, arguments);
  return this;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/nodes.js
/* harmony default export */ var selection_nodes = (function() {
  var nodes = new Array(this.size()), i = -1;
  this.each(function() { nodes[++i] = this; });
  return nodes;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/node.js
/* harmony default export */ var selection_node = (function() {

  for (var groups = this._groups, j = 0, m = groups.length; j < m; ++j) {
    for (var group = groups[j], i = 0, n = group.length; i < n; ++i) {
      var node = group[i];
      if (node) return node;
    }
  }

  return null;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/size.js
/* harmony default export */ var selection_size = (function() {
  var size = 0;
  this.each(function() { ++size; });
  return size;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/empty.js
/* harmony default export */ var selection_empty = (function() {
  return !this.node();
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/each.js
/* harmony default export */ var each = (function(callback) {

  for (var groups = this._groups, j = 0, m = groups.length; j < m; ++j) {
    for (var group = groups[j], i = 0, n = group.length, node; i < n; ++i) {
      if (node = group[i]) callback.call(node, node.__data__, i, group);
    }
  }

  return this;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/attr.js


function attrRemove(name) {
  return function() {
    this.removeAttribute(name);
  };
}

function attrRemoveNS(fullname) {
  return function() {
    this.removeAttributeNS(fullname.space, fullname.local);
  };
}

function attrConstant(name, value) {
  return function() {
    this.setAttribute(name, value);
  };
}

function attrConstantNS(fullname, value) {
  return function() {
    this.setAttributeNS(fullname.space, fullname.local, value);
  };
}

function attrFunction(name, value) {
  return function() {
    var v = value.apply(this, arguments);
    if (v == null) this.removeAttribute(name);
    else this.setAttribute(name, v);
  };
}

function attrFunctionNS(fullname, value) {
  return function() {
    var v = value.apply(this, arguments);
    if (v == null) this.removeAttributeNS(fullname.space, fullname.local);
    else this.setAttributeNS(fullname.space, fullname.local, v);
  };
}

/* harmony default export */ var attr = (function(name, value) {
  var fullname = namespace(name);

  if (arguments.length < 2) {
    var node = this.node();
    return fullname.local
        ? node.getAttributeNS(fullname.space, fullname.local)
        : node.getAttribute(fullname);
  }

  return this.each((value == null
      ? (fullname.local ? attrRemoveNS : attrRemove) : (typeof value === "function"
      ? (fullname.local ? attrFunctionNS : attrFunction)
      : (fullname.local ? attrConstantNS : attrConstant)))(fullname, value));
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/window.js
/* harmony default export */ var src_window = (function(node) {
  return (node.ownerDocument && node.ownerDocument.defaultView) // node is a Node
      || (node.document && node) // node is a Window
      || node.defaultView; // node is a Document
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/style.js


function styleRemove(name) {
  return function() {
    this.style.removeProperty(name);
  };
}

function styleConstant(name, value, priority) {
  return function() {
    this.style.setProperty(name, value, priority);
  };
}

function styleFunction(name, value, priority) {
  return function() {
    var v = value.apply(this, arguments);
    if (v == null) this.style.removeProperty(name);
    else this.style.setProperty(name, v, priority);
  };
}

/* harmony default export */ var selection_style = (function(name, value, priority) {
  return arguments.length > 1
      ? this.each((value == null
            ? styleRemove : typeof value === "function"
            ? styleFunction
            : styleConstant)(name, value, priority == null ? "" : priority))
      : styleValue(this.node(), name);
});

function styleValue(node, name) {
  return node.style.getPropertyValue(name)
      || src_window(node).getComputedStyle(node, null).getPropertyValue(name);
}

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/property.js
function propertyRemove(name) {
  return function() {
    delete this[name];
  };
}

function propertyConstant(name, value) {
  return function() {
    this[name] = value;
  };
}

function propertyFunction(name, value) {
  return function() {
    var v = value.apply(this, arguments);
    if (v == null) delete this[name];
    else this[name] = v;
  };
}

/* harmony default export */ var property = (function(name, value) {
  return arguments.length > 1
      ? this.each((value == null
          ? propertyRemove : typeof value === "function"
          ? propertyFunction
          : propertyConstant)(name, value))
      : this.node()[name];
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/classed.js
function classArray(string) {
  return string.trim().split(/^|\s+/);
}

function classList(node) {
  return node.classList || new ClassList(node);
}

function ClassList(node) {
  this._node = node;
  this._names = classArray(node.getAttribute("class") || "");
}

ClassList.prototype = {
  add: function(name) {
    var i = this._names.indexOf(name);
    if (i < 0) {
      this._names.push(name);
      this._node.setAttribute("class", this._names.join(" "));
    }
  },
  remove: function(name) {
    var i = this._names.indexOf(name);
    if (i >= 0) {
      this._names.splice(i, 1);
      this._node.setAttribute("class", this._names.join(" "));
    }
  },
  contains: function(name) {
    return this._names.indexOf(name) >= 0;
  }
};

function classedAdd(node, names) {
  var list = classList(node), i = -1, n = names.length;
  while (++i < n) list.add(names[i]);
}

function classedRemove(node, names) {
  var list = classList(node), i = -1, n = names.length;
  while (++i < n) list.remove(names[i]);
}

function classedTrue(names) {
  return function() {
    classedAdd(this, names);
  };
}

function classedFalse(names) {
  return function() {
    classedRemove(this, names);
  };
}

function classedFunction(names, value) {
  return function() {
    (value.apply(this, arguments) ? classedAdd : classedRemove)(this, names);
  };
}

/* harmony default export */ var classed = (function(name, value) {
  var names = classArray(name + "");

  if (arguments.length < 2) {
    var list = classList(this.node()), i = -1, n = names.length;
    while (++i < n) if (!list.contains(names[i])) return false;
    return true;
  }

  return this.each((typeof value === "function"
      ? classedFunction : value
      ? classedTrue
      : classedFalse)(names, value));
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/text.js
function textRemove() {
  this.textContent = "";
}

function textConstant(value) {
  return function() {
    this.textContent = value;
  };
}

function textFunction(value) {
  return function() {
    var v = value.apply(this, arguments);
    this.textContent = v == null ? "" : v;
  };
}

/* harmony default export */ var selection_text = (function(value) {
  return arguments.length
      ? this.each(value == null
          ? textRemove : (typeof value === "function"
          ? textFunction
          : textConstant)(value))
      : this.node().textContent;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/html.js
function htmlRemove() {
  this.innerHTML = "";
}

function htmlConstant(value) {
  return function() {
    this.innerHTML = value;
  };
}

function htmlFunction(value) {
  return function() {
    var v = value.apply(this, arguments);
    this.innerHTML = v == null ? "" : v;
  };
}

/* harmony default export */ var html = (function(value) {
  return arguments.length
      ? this.each(value == null
          ? htmlRemove : (typeof value === "function"
          ? htmlFunction
          : htmlConstant)(value))
      : this.node().innerHTML;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/raise.js
function raise() {
  if (this.nextSibling) this.parentNode.appendChild(this);
}

/* harmony default export */ var selection_raise = (function() {
  return this.each(raise);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/lower.js
function lower_lower() {
  if (this.previousSibling) this.parentNode.insertBefore(this, this.parentNode.firstChild);
}

/* harmony default export */ var selection_lower = (function() {
  return this.each(lower_lower);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/append.js


/* harmony default export */ var append = (function(name) {
  var create = typeof name === "function" ? name : creator(name);
  return this.select(function() {
    return this.appendChild(create.apply(this, arguments));
  });
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/insert.js



function constantNull() {
  return null;
}

/* harmony default export */ var insert = (function(name, before) {
  var create = typeof name === "function" ? name : creator(name),
      select = before == null ? constantNull : typeof before === "function" ? before : src_selector(before);
  return this.select(function() {
    return this.insertBefore(create.apply(this, arguments), select.apply(this, arguments) || null);
  });
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/remove.js
function remove() {
  var parent = this.parentNode;
  if (parent) parent.removeChild(this);
}

/* harmony default export */ var selection_remove = (function() {
  return this.each(remove);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/clone.js
function selection_cloneShallow() {
  return this.parentNode.insertBefore(this.cloneNode(false), this.nextSibling);
}

function selection_cloneDeep() {
  return this.parentNode.insertBefore(this.cloneNode(true), this.nextSibling);
}

/* harmony default export */ var clone = (function(deep) {
  return this.select(deep ? selection_cloneDeep : selection_cloneShallow);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/datum.js
/* harmony default export */ var datum = (function(value) {
  return arguments.length
      ? this.property("__data__", value)
      : this.node().__data__;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/on.js
var filterEvents = {};

var on_event = null;

if (typeof document !== "undefined") {
  var on_element = document.documentElement;
  if (!("onmouseenter" in on_element)) {
    filterEvents = {mouseenter: "mouseover", mouseleave: "mouseout"};
  }
}

function filterContextListener(listener, index, group) {
  listener = contextListener(listener, index, group);
  return function(event) {
    var related = event.relatedTarget;
    if (!related || (related !== this && !(related.compareDocumentPosition(this) & 8))) {
      listener.call(this, event);
    }
  };
}

function contextListener(listener, index, group) {
  return function(event1) {
    var event0 = on_event; // Events can be reentrant (e.g., focus).
    on_event = event1;
    try {
      listener.call(this, this.__data__, index, group);
    } finally {
      on_event = event0;
    }
  };
}

function parseTypenames(typenames) {
  return typenames.trim().split(/^|\s+/).map(function(t) {
    var name = "", i = t.indexOf(".");
    if (i >= 0) name = t.slice(i + 1), t = t.slice(0, i);
    return {type: t, name: name};
  });
}

function onRemove(typename) {
  return function() {
    var on = this.__on;
    if (!on) return;
    for (var j = 0, i = -1, m = on.length, o; j < m; ++j) {
      if (o = on[j], (!typename.type || o.type === typename.type) && o.name === typename.name) {
        this.removeEventListener(o.type, o.listener, o.capture);
      } else {
        on[++i] = o;
      }
    }
    if (++i) on.length = i;
    else delete this.__on;
  };
}

function onAdd(typename, value, capture) {
  var wrap = filterEvents.hasOwnProperty(typename.type) ? filterContextListener : contextListener;
  return function(d, i, group) {
    var on = this.__on, o, listener = wrap(value, i, group);
    if (on) for (var j = 0, m = on.length; j < m; ++j) {
      if ((o = on[j]).type === typename.type && o.name === typename.name) {
        this.removeEventListener(o.type, o.listener, o.capture);
        this.addEventListener(o.type, o.listener = listener, o.capture = capture);
        o.value = value;
        return;
      }
    }
    this.addEventListener(typename.type, listener, capture);
    o = {type: typename.type, name: typename.name, value: value, listener: listener, capture: capture};
    if (!on) this.__on = [o];
    else on.push(o);
  };
}

/* harmony default export */ var selection_on = (function(typename, value, capture) {
  var typenames = parseTypenames(typename + ""), i, n = typenames.length, t;

  if (arguments.length < 2) {
    var on = this.node().__on;
    if (on) for (var j = 0, m = on.length, o; j < m; ++j) {
      for (i = 0, o = on[j]; i < n; ++i) {
        if ((t = typenames[i]).type === o.type && t.name === o.name) {
          return o.value;
        }
      }
    }
    return;
  }

  on = value ? onAdd : onRemove;
  if (capture == null) capture = false;
  for (i = 0; i < n; ++i) this.each(on(typenames[i], value, capture));
  return this;
});

function customEvent(event1, listener, that, args) {
  var event0 = on_event;
  event1.sourceEvent = on_event;
  on_event = event1;
  try {
    return listener.apply(that, args);
  } finally {
    on_event = event0;
  }
}

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/dispatch.js


function dispatchEvent(node, type, params) {
  var window = src_window(node),
      event = window.CustomEvent;

  if (typeof event === "function") {
    event = new event(type, params);
  } else {
    event = window.document.createEvent("Event");
    if (params) event.initEvent(type, params.bubbles, params.cancelable), event.detail = params.detail;
    else event.initEvent(type, false, false);
  }

  node.dispatchEvent(event);
}

function dispatchConstant(type, params) {
  return function() {
    return dispatchEvent(this, type, params);
  };
}

function dispatchFunction(type, params) {
  return function() {
    return dispatchEvent(this, type, params.apply(this, arguments));
  };
}

/* harmony default export */ var dispatch = (function(type, params) {
  return this.each((typeof params === "function"
      ? dispatchFunction
      : dispatchConstant)(type, params));
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selection/index.js
































var selection_root = [null];

function Selection(groups, parents) {
  this._groups = groups;
  this._parents = parents;
}

function selection_selection() {
  return new Selection([[document.documentElement]], selection_root);
}

Selection.prototype = selection_selection.prototype = {
  constructor: Selection,
  select: selection_select,
  selectAll: selectAll,
  filter: selection_filter,
  data: selection_data,
  enter: selection_enter,
  exit: selection_exit,
  join: join,
  merge: selection_merge,
  order: selection_order,
  sort: selection_sort,
  call: call,
  nodes: selection_nodes,
  node: selection_node,
  size: selection_size,
  empty: selection_empty,
  each: each,
  attr: attr,
  style: selection_style,
  property: property,
  classed: classed,
  text: selection_text,
  html: html,
  raise: selection_raise,
  lower: selection_lower,
  append: append,
  insert: insert,
  remove: selection_remove,
  clone: clone,
  datum: datum,
  on: selection_on,
  dispatch: dispatch
};

/* harmony default export */ var src_selection = (selection_selection);

// CONCATENATED MODULE: ./node_modules/d3-selection/src/select.js


/* harmony default export */ var src_select = (function(selector) {
  return typeof selector === "string"
      ? new Selection([[document.querySelector(selector)]], [document.documentElement])
      : new Selection([[selector]], selection_root);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/create.js



/* harmony default export */ var src_create = (function(name) {
  return src_select(creator(name).call(document.documentElement));
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/local.js
var nextId = 0;

function local() {
  return new Local;
}

function Local() {
  this._ = "@" + (++nextId).toString(36);
}

Local.prototype = local.prototype = {
  constructor: Local,
  get: function(node) {
    var id = this._;
    while (!(id in node)) if (!(node = node.parentNode)) return;
    return node[id];
  },
  set: function(node, value) {
    return node[this._] = value;
  },
  remove: function(node) {
    return this._ in node && delete node[this._];
  },
  toString: function() {
    return this._;
  }
};

// CONCATENATED MODULE: ./node_modules/d3-selection/src/sourceEvent.js


/* harmony default export */ var sourceEvent = (function() {
  var current = on_event, source;
  while (source = current.sourceEvent) current = source;
  return current;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/point.js
/* harmony default export */ var src_point = (function(node, event) {
  var svg = node.ownerSVGElement || node;

  if (svg.createSVGPoint) {
    var point = svg.createSVGPoint();
    point.x = event.clientX, point.y = event.clientY;
    point = point.matrixTransform(node.getScreenCTM().inverse());
    return [point.x, point.y];
  }

  var rect = node.getBoundingClientRect();
  return [event.clientX - rect.left - node.clientLeft, event.clientY - rect.top - node.clientTop];
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/mouse.js



/* harmony default export */ var mouse = (function(node) {
  var event = sourceEvent();
  if (event.changedTouches) event = event.changedTouches[0];
  return src_point(node, event);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/selectAll.js


/* harmony default export */ var src_selectAll = (function(selector) {
  return typeof selector === "string"
      ? new Selection([document.querySelectorAll(selector)], [document.documentElement])
      : new Selection([selector == null ? [] : selector], selection_root);
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/touch.js



/* harmony default export */ var src_touch = (function(node, touches, identifier) {
  if (arguments.length < 3) identifier = touches, touches = sourceEvent().changedTouches;

  for (var i = 0, n = touches ? touches.length : 0, touch; i < n; ++i) {
    if ((touch = touches[i]).identifier === identifier) {
      return src_point(node, touch);
    }
  }

  return null;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/touches.js



/* harmony default export */ var src_touches = (function(node, touches) {
  if (touches == null) touches = sourceEvent().touches;

  for (var i = 0, n = touches ? touches.length : 0, points = new Array(n); i < n; ++i) {
    points[i] = src_point(node, touches[i]);
  }

  return points;
});

// CONCATENATED MODULE: ./node_modules/d3-selection/src/index.js



















// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/cluster.js
function defaultSeparation(a, b) {
  return a.parent === b.parent ? 1 : 2;
}

function meanX(children) {
  return children.reduce(meanXReduce, 0) / children.length;
}

function meanXReduce(x, c) {
  return x + c.x;
}

function maxY(children) {
  return 1 + children.reduce(maxYReduce, 0);
}

function maxYReduce(y, c) {
  return Math.max(y, c.y);
}

function leafLeft(node) {
  var children;
  while (children = node.children) node = children[0];
  return node;
}

function leafRight(node) {
  var children;
  while (children = node.children) node = children[children.length - 1];
  return node;
}

/* harmony default export */ var cluster = (function() {
  var separation = defaultSeparation,
      dx = 1,
      dy = 1,
      nodeSize = false;

  function cluster(root) {
    var previousNode,
        x = 0;

    // First walk, computing the initial x & y values.
    root.eachAfter(function(node) {
      var children = node.children;
      if (children) {
        node.x = meanX(children);
        node.y = maxY(children);
      } else {
        node.x = previousNode ? x += separation(node, previousNode) : 0;
        node.y = 0;
        previousNode = node;
      }
    });

    var left = leafLeft(root),
        right = leafRight(root),
        x0 = left.x - separation(left, right) / 2,
        x1 = right.x + separation(right, left) / 2;

    // Second walk, normalizing x & y to the desired size.
    return root.eachAfter(nodeSize ? function(node) {
      node.x = (node.x - root.x) * dx;
      node.y = (root.y - node.y) * dy;
    } : function(node) {
      node.x = (node.x - x0) / (x1 - x0) * dx;
      node.y = (1 - (root.y ? node.y / root.y : 1)) * dy;
    });
  }

  cluster.separation = function(x) {
    return arguments.length ? (separation = x, cluster) : separation;
  };

  cluster.size = function(x) {
    return arguments.length ? (nodeSize = false, dx = +x[0], dy = +x[1], cluster) : (nodeSize ? null : [dx, dy]);
  };

  cluster.nodeSize = function(x) {
    return arguments.length ? (nodeSize = true, dx = +x[0], dy = +x[1], cluster) : (nodeSize ? [dx, dy] : null);
  };

  return cluster;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/count.js
function count(node) {
  var sum = 0,
      children = node.children,
      i = children && children.length;
  if (!i) sum = 1;
  else while (--i >= 0) sum += children[i].value;
  node.value = sum;
}

/* harmony default export */ var hierarchy_count = (function() {
  return this.eachAfter(count);
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/each.js
/* harmony default export */ var hierarchy_each = (function(callback) {
  var node = this, current, next = [node], children, i, n;
  do {
    current = next.reverse(), next = [];
    while (node = current.pop()) {
      callback(node), children = node.children;
      if (children) for (i = 0, n = children.length; i < n; ++i) {
        next.push(children[i]);
      }
    }
  } while (next.length);
  return this;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/eachBefore.js
/* harmony default export */ var eachBefore = (function(callback) {
  var node = this, nodes = [node], children, i;
  while (node = nodes.pop()) {
    callback(node), children = node.children;
    if (children) for (i = children.length - 1; i >= 0; --i) {
      nodes.push(children[i]);
    }
  }
  return this;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/eachAfter.js
/* harmony default export */ var eachAfter = (function(callback) {
  var node = this, nodes = [node], next = [], children, i, n;
  while (node = nodes.pop()) {
    next.push(node), children = node.children;
    if (children) for (i = 0, n = children.length; i < n; ++i) {
      nodes.push(children[i]);
    }
  }
  while (node = next.pop()) {
    callback(node);
  }
  return this;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/sum.js
/* harmony default export */ var hierarchy_sum = (function(value) {
  return this.eachAfter(function(node) {
    var sum = +value(node.data) || 0,
        children = node.children,
        i = children && children.length;
    while (--i >= 0) sum += children[i].value;
    node.value = sum;
  });
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/sort.js
/* harmony default export */ var hierarchy_sort = (function(compare) {
  return this.eachBefore(function(node) {
    if (node.children) {
      node.children.sort(compare);
    }
  });
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/path.js
/* harmony default export */ var path = (function(end) {
  var start = this,
      ancestor = leastCommonAncestor(start, end),
      nodes = [start];
  while (start !== ancestor) {
    start = start.parent;
    nodes.push(start);
  }
  var k = nodes.length;
  while (end !== ancestor) {
    nodes.splice(k, 0, end);
    end = end.parent;
  }
  return nodes;
});

function leastCommonAncestor(a, b) {
  if (a === b) return a;
  var aNodes = a.ancestors(),
      bNodes = b.ancestors(),
      c = null;
  a = aNodes.pop();
  b = bNodes.pop();
  while (a === b) {
    c = a;
    a = aNodes.pop();
    b = bNodes.pop();
  }
  return c;
}

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/ancestors.js
/* harmony default export */ var ancestors = (function() {
  var node = this, nodes = [node];
  while (node = node.parent) {
    nodes.push(node);
  }
  return nodes;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/descendants.js
/* harmony default export */ var descendants = (function() {
  var nodes = [];
  this.each(function(node) {
    nodes.push(node);
  });
  return nodes;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/leaves.js
/* harmony default export */ var leaves = (function() {
  var leaves = [];
  this.eachBefore(function(node) {
    if (!node.children) {
      leaves.push(node);
    }
  });
  return leaves;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/links.js
/* harmony default export */ var links = (function() {
  var root = this, links = [];
  root.each(function(node) {
    if (node !== root) { // Don’t include the root’s parent, if any.
      links.push({source: node.parent, target: node});
    }
  });
  return links;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/hierarchy/index.js












function hierarchy(data, children) {
  var root = new Node(data),
      valued = +data.value && (root.value = data.value),
      node,
      nodes = [root],
      child,
      childs,
      i,
      n;

  if (children == null) children = defaultChildren;

  while (node = nodes.pop()) {
    if (valued) node.value = +node.data.value;
    if ((childs = children(node.data)) && (n = childs.length)) {
      node.children = new Array(n);
      for (i = n - 1; i >= 0; --i) {
        nodes.push(child = node.children[i] = new Node(childs[i]));
        child.parent = node;
        child.depth = node.depth + 1;
      }
    }
  }

  return root.eachBefore(computeHeight);
}

function node_copy() {
  return hierarchy(this).eachBefore(copyData);
}

function defaultChildren(d) {
  return d.children;
}

function copyData(node) {
  node.data = node.data.data;
}

function computeHeight(node) {
  var height = 0;
  do node.height = height;
  while ((node = node.parent) && (node.height < ++height));
}

function Node(data) {
  this.data = data;
  this.depth =
  this.height = 0;
  this.parent = null;
}

Node.prototype = hierarchy.prototype = {
  constructor: Node,
  count: hierarchy_count,
  each: hierarchy_each,
  eachAfter: eachAfter,
  eachBefore: eachBefore,
  sum: hierarchy_sum,
  sort: hierarchy_sort,
  path: path,
  ancestors: ancestors,
  descendants: descendants,
  leaves: leaves,
  links: links,
  copy: node_copy
};

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/array.js
var slice = Array.prototype.slice;

function shuffle(array) {
  var m = array.length,
      t,
      i;

  while (m) {
    i = Math.random() * m-- | 0;
    t = array[m];
    array[m] = array[i];
    array[i] = t;
  }

  return array;
}

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/pack/enclose.js


/* harmony default export */ var enclose = (function(circles) {
  var i = 0, n = (circles = shuffle(slice.call(circles))).length, B = [], p, e;

  while (i < n) {
    p = circles[i];
    if (e && enclosesWeak(e, p)) ++i;
    else e = encloseBasis(B = extendBasis(B, p)), i = 0;
  }

  return e;
});

function extendBasis(B, p) {
  var i, j;

  if (enclosesWeakAll(p, B)) return [p];

  // If we get here then B must have at least one element.
  for (i = 0; i < B.length; ++i) {
    if (enclosesNot(p, B[i])
        && enclosesWeakAll(encloseBasis2(B[i], p), B)) {
      return [B[i], p];
    }
  }

  // If we get here then B must have at least two elements.
  for (i = 0; i < B.length - 1; ++i) {
    for (j = i + 1; j < B.length; ++j) {
      if (enclosesNot(encloseBasis2(B[i], B[j]), p)
          && enclosesNot(encloseBasis2(B[i], p), B[j])
          && enclosesNot(encloseBasis2(B[j], p), B[i])
          && enclosesWeakAll(encloseBasis3(B[i], B[j], p), B)) {
        return [B[i], B[j], p];
      }
    }
  }

  // If we get here then something is very wrong.
  throw new Error;
}

function enclosesNot(a, b) {
  var dr = a.r - b.r, dx = b.x - a.x, dy = b.y - a.y;
  return dr < 0 || dr * dr < dx * dx + dy * dy;
}

function enclosesWeak(a, b) {
  var dr = a.r - b.r + 1e-6, dx = b.x - a.x, dy = b.y - a.y;
  return dr > 0 && dr * dr > dx * dx + dy * dy;
}

function enclosesWeakAll(a, B) {
  for (var i = 0; i < B.length; ++i) {
    if (!enclosesWeak(a, B[i])) {
      return false;
    }
  }
  return true;
}

function encloseBasis(B) {
  switch (B.length) {
    case 1: return encloseBasis1(B[0]);
    case 2: return encloseBasis2(B[0], B[1]);
    case 3: return encloseBasis3(B[0], B[1], B[2]);
  }
}

function encloseBasis1(a) {
  return {
    x: a.x,
    y: a.y,
    r: a.r
  };
}

function encloseBasis2(a, b) {
  var x1 = a.x, y1 = a.y, r1 = a.r,
      x2 = b.x, y2 = b.y, r2 = b.r,
      x21 = x2 - x1, y21 = y2 - y1, r21 = r2 - r1,
      l = Math.sqrt(x21 * x21 + y21 * y21);
  return {
    x: (x1 + x2 + x21 / l * r21) / 2,
    y: (y1 + y2 + y21 / l * r21) / 2,
    r: (l + r1 + r2) / 2
  };
}

function encloseBasis3(a, b, c) {
  var x1 = a.x, y1 = a.y, r1 = a.r,
      x2 = b.x, y2 = b.y, r2 = b.r,
      x3 = c.x, y3 = c.y, r3 = c.r,
      a2 = x1 - x2,
      a3 = x1 - x3,
      b2 = y1 - y2,
      b3 = y1 - y3,
      c2 = r2 - r1,
      c3 = r3 - r1,
      d1 = x1 * x1 + y1 * y1 - r1 * r1,
      d2 = d1 - x2 * x2 - y2 * y2 + r2 * r2,
      d3 = d1 - x3 * x3 - y3 * y3 + r3 * r3,
      ab = a3 * b2 - a2 * b3,
      xa = (b2 * d3 - b3 * d2) / (ab * 2) - x1,
      xb = (b3 * c2 - b2 * c3) / ab,
      ya = (a3 * d2 - a2 * d3) / (ab * 2) - y1,
      yb = (a2 * c3 - a3 * c2) / ab,
      A = xb * xb + yb * yb - 1,
      B = 2 * (r1 + xa * xb + ya * yb),
      C = xa * xa + ya * ya - r1 * r1,
      r = -(A ? (B + Math.sqrt(B * B - 4 * A * C)) / (2 * A) : C / B);
  return {
    x: x1 + xa + xb * r,
    y: y1 + ya + yb * r,
    r: r
  };
}

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/pack/siblings.js


function place(b, a, c) {
  var dx = b.x - a.x, x, a2,
      dy = b.y - a.y, y, b2,
      d2 = dx * dx + dy * dy;
  if (d2) {
    a2 = a.r + c.r, a2 *= a2;
    b2 = b.r + c.r, b2 *= b2;
    if (a2 > b2) {
      x = (d2 + b2 - a2) / (2 * d2);
      y = Math.sqrt(Math.max(0, b2 / d2 - x * x));
      c.x = b.x - x * dx - y * dy;
      c.y = b.y - x * dy + y * dx;
    } else {
      x = (d2 + a2 - b2) / (2 * d2);
      y = Math.sqrt(Math.max(0, a2 / d2 - x * x));
      c.x = a.x + x * dx - y * dy;
      c.y = a.y + x * dy + y * dx;
    }
  } else {
    c.x = a.x + c.r;
    c.y = a.y;
  }
}

function intersects(a, b) {
  var dr = a.r + b.r - 1e-6, dx = b.x - a.x, dy = b.y - a.y;
  return dr > 0 && dr * dr > dx * dx + dy * dy;
}

function score(node) {
  var a = node._,
      b = node.next._,
      ab = a.r + b.r,
      dx = (a.x * b.r + b.x * a.r) / ab,
      dy = (a.y * b.r + b.y * a.r) / ab;
  return dx * dx + dy * dy;
}

function siblings_Node(circle) {
  this._ = circle;
  this.next = null;
  this.previous = null;
}

function packEnclose(circles) {
  if (!(n = circles.length)) return 0;

  var a, b, c, n, aa, ca, i, j, k, sj, sk;

  // Place the first circle.
  a = circles[0], a.x = 0, a.y = 0;
  if (!(n > 1)) return a.r;

  // Place the second circle.
  b = circles[1], a.x = -b.r, b.x = a.r, b.y = 0;
  if (!(n > 2)) return a.r + b.r;

  // Place the third circle.
  place(b, a, c = circles[2]);

  // Initialize the front-chain using the first three circles a, b and c.
  a = new siblings_Node(a), b = new siblings_Node(b), c = new siblings_Node(c);
  a.next = c.previous = b;
  b.next = a.previous = c;
  c.next = b.previous = a;

  // Attempt to place each remaining circle…
  pack: for (i = 3; i < n; ++i) {
    place(a._, b._, c = circles[i]), c = new siblings_Node(c);

    // Find the closest intersecting circle on the front-chain, if any.
    // “Closeness” is determined by linear distance along the front-chain.
    // “Ahead” or “behind” is likewise determined by linear distance.
    j = b.next, k = a.previous, sj = b._.r, sk = a._.r;
    do {
      if (sj <= sk) {
        if (intersects(j._, c._)) {
          b = j, a.next = b, b.previous = a, --i;
          continue pack;
        }
        sj += j._.r, j = j.next;
      } else {
        if (intersects(k._, c._)) {
          a = k, a.next = b, b.previous = a, --i;
          continue pack;
        }
        sk += k._.r, k = k.previous;
      }
    } while (j !== k.next);

    // Success! Insert the new circle c between a and b.
    c.previous = a, c.next = b, a.next = b.previous = b = c;

    // Compute the new closest circle pair to the centroid.
    aa = score(a);
    while ((c = c.next) !== b) {
      if ((ca = score(c)) < aa) {
        a = c, aa = ca;
      }
    }
    b = a.next;
  }

  // Compute the enclosing circle of the front chain.
  a = [b._], c = b; while ((c = c.next) !== b) a.push(c._); c = enclose(a);

  // Translate the circles to put the enclosing circle around the origin.
  for (i = 0; i < n; ++i) a = circles[i], a.x -= c.x, a.y -= c.y;

  return c.r;
}

/* harmony default export */ var siblings = (function(circles) {
  packEnclose(circles);
  return circles;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/accessors.js
function optional(f) {
  return f == null ? null : required(f);
}

function required(f) {
  if (typeof f !== "function") throw new Error;
  return f;
}

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/constant.js
function constantZero() {
  return 0;
}

/* harmony default export */ var src_constant = (function(x) {
  return function() {
    return x;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/pack/index.js




function defaultRadius(d) {
  return Math.sqrt(d.value);
}

/* harmony default export */ var src_pack = (function() {
  var radius = null,
      dx = 1,
      dy = 1,
      padding = constantZero;

  function pack(root) {
    root.x = dx / 2, root.y = dy / 2;
    if (radius) {
      root.eachBefore(radiusLeaf(radius))
          .eachAfter(packChildren(padding, 0.5))
          .eachBefore(translateChild(1));
    } else {
      root.eachBefore(radiusLeaf(defaultRadius))
          .eachAfter(packChildren(constantZero, 1))
          .eachAfter(packChildren(padding, root.r / Math.min(dx, dy)))
          .eachBefore(translateChild(Math.min(dx, dy) / (2 * root.r)));
    }
    return root;
  }

  pack.radius = function(x) {
    return arguments.length ? (radius = optional(x), pack) : radius;
  };

  pack.size = function(x) {
    return arguments.length ? (dx = +x[0], dy = +x[1], pack) : [dx, dy];
  };

  pack.padding = function(x) {
    return arguments.length ? (padding = typeof x === "function" ? x : src_constant(+x), pack) : padding;
  };

  return pack;
});

function radiusLeaf(radius) {
  return function(node) {
    if (!node.children) {
      node.r = Math.max(0, +radius(node) || 0);
    }
  };
}

function packChildren(padding, k) {
  return function(node) {
    if (children = node.children) {
      var children,
          i,
          n = children.length,
          r = padding(node) * k || 0,
          e;

      if (r) for (i = 0; i < n; ++i) children[i].r += r;
      e = packEnclose(children);
      if (r) for (i = 0; i < n; ++i) children[i].r -= r;
      node.r = e + r;
    }
  };
}

function translateChild(k) {
  return function(node) {
    var parent = node.parent;
    node.r *= k;
    if (parent) {
      node.x = parent.x + k * node.x;
      node.y = parent.y + k * node.y;
    }
  };
}

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/treemap/round.js
/* harmony default export */ var treemap_round = (function(node) {
  node.x0 = Math.round(node.x0);
  node.y0 = Math.round(node.y0);
  node.x1 = Math.round(node.x1);
  node.y1 = Math.round(node.y1);
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/treemap/dice.js
/* harmony default export */ var dice = (function(parent, x0, y0, x1, y1) {
  var nodes = parent.children,
      node,
      i = -1,
      n = nodes.length,
      k = parent.value && (x1 - x0) / parent.value;

  while (++i < n) {
    node = nodes[i], node.y0 = y0, node.y1 = y1;
    node.x0 = x0, node.x1 = x0 += node.value * k;
  }
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/partition.js



/* harmony default export */ var src_partition = (function() {
  var dx = 1,
      dy = 1,
      padding = 0,
      round = false;

  function partition(root) {
    var n = root.height + 1;
    root.x0 =
    root.y0 = padding;
    root.x1 = dx;
    root.y1 = dy / n;
    root.eachBefore(positionNode(dy, n));
    if (round) root.eachBefore(treemap_round);
    return root;
  }

  function positionNode(dy, n) {
    return function(node) {
      if (node.children) {
        dice(node, node.x0, dy * (node.depth + 1) / n, node.x1, dy * (node.depth + 2) / n);
      }
      var x0 = node.x0,
          y0 = node.y0,
          x1 = node.x1 - padding,
          y1 = node.y1 - padding;
      if (x1 < x0) x0 = x1 = (x0 + x1) / 2;
      if (y1 < y0) y0 = y1 = (y0 + y1) / 2;
      node.x0 = x0;
      node.y0 = y0;
      node.x1 = x1;
      node.y1 = y1;
    };
  }

  partition.round = function(x) {
    return arguments.length ? (round = !!x, partition) : round;
  };

  partition.size = function(x) {
    return arguments.length ? (dx = +x[0], dy = +x[1], partition) : [dx, dy];
  };

  partition.padding = function(x) {
    return arguments.length ? (padding = +x, partition) : padding;
  };

  return partition;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/stratify.js



var stratify_keyPrefix = "$", // Protect against keys like “__proto__”.
    preroot = {depth: -1},
    ambiguous = {};

function defaultId(d) {
  return d.id;
}

function defaultParentId(d) {
  return d.parentId;
}

/* harmony default export */ var src_stratify = (function() {
  var id = defaultId,
      parentId = defaultParentId;

  function stratify(data) {
    var d,
        i,
        n = data.length,
        root,
        parent,
        node,
        nodes = new Array(n),
        nodeId,
        nodeKey,
        nodeByKey = {};

    for (i = 0; i < n; ++i) {
      d = data[i], node = nodes[i] = new Node(d);
      if ((nodeId = id(d, i, data)) != null && (nodeId += "")) {
        nodeKey = stratify_keyPrefix + (node.id = nodeId);
        nodeByKey[nodeKey] = nodeKey in nodeByKey ? ambiguous : node;
      }
    }

    for (i = 0; i < n; ++i) {
      node = nodes[i], nodeId = parentId(data[i], i, data);
      if (nodeId == null || !(nodeId += "")) {
        if (root) throw new Error("multiple roots");
        root = node;
      } else {
        parent = nodeByKey[stratify_keyPrefix + nodeId];
        if (!parent) throw new Error("missing: " + nodeId);
        if (parent === ambiguous) throw new Error("ambiguous: " + nodeId);
        if (parent.children) parent.children.push(node);
        else parent.children = [node];
        node.parent = parent;
      }
    }

    if (!root) throw new Error("no root");
    root.parent = preroot;
    root.eachBefore(function(node) { node.depth = node.parent.depth + 1; --n; }).eachBefore(computeHeight);
    root.parent = null;
    if (n > 0) throw new Error("cycle");

    return root;
  }

  stratify.id = function(x) {
    return arguments.length ? (id = required(x), stratify) : id;
  };

  stratify.parentId = function(x) {
    return arguments.length ? (parentId = required(x), stratify) : parentId;
  };

  return stratify;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/tree.js


function tree_defaultSeparation(a, b) {
  return a.parent === b.parent ? 1 : 2;
}

// function radialSeparation(a, b) {
//   return (a.parent === b.parent ? 1 : 2) / a.depth;
// }

// This function is used to traverse the left contour of a subtree (or
// subforest). It returns the successor of v on this contour. This successor is
// either given by the leftmost child of v or by the thread of v. The function
// returns null if and only if v is on the highest level of its subtree.
function nextLeft(v) {
  var children = v.children;
  return children ? children[0] : v.t;
}

// This function works analogously to nextLeft.
function nextRight(v) {
  var children = v.children;
  return children ? children[children.length - 1] : v.t;
}

// Shifts the current subtree rooted at w+. This is done by increasing
// prelim(w+) and mod(w+) by shift.
function moveSubtree(wm, wp, shift) {
  var change = shift / (wp.i - wm.i);
  wp.c -= change;
  wp.s += shift;
  wm.c += change;
  wp.z += shift;
  wp.m += shift;
}

// All other shifts, applied to the smaller subtrees between w- and w+, are
// performed by this function. To prepare the shifts, we have to adjust
// change(w+), shift(w+), and change(w-).
function executeShifts(v) {
  var shift = 0,
      change = 0,
      children = v.children,
      i = children.length,
      w;
  while (--i >= 0) {
    w = children[i];
    w.z += shift;
    w.m += shift;
    shift += w.s + (change += w.c);
  }
}

// If vi-’s ancestor is a sibling of v, returns vi-’s ancestor. Otherwise,
// returns the specified (default) ancestor.
function nextAncestor(vim, v, ancestor) {
  return vim.a.parent === v.parent ? vim.a : ancestor;
}

function TreeNode(node, i) {
  this._ = node;
  this.parent = null;
  this.children = null;
  this.A = null; // default ancestor
  this.a = this; // ancestor
  this.z = 0; // prelim
  this.m = 0; // mod
  this.c = 0; // change
  this.s = 0; // shift
  this.t = null; // thread
  this.i = i; // number
}

TreeNode.prototype = Object.create(Node.prototype);

function treeRoot(root) {
  var tree = new TreeNode(root, 0),
      node,
      nodes = [tree],
      child,
      children,
      i,
      n;

  while (node = nodes.pop()) {
    if (children = node._.children) {
      node.children = new Array(n = children.length);
      for (i = n - 1; i >= 0; --i) {
        nodes.push(child = node.children[i] = new TreeNode(children[i], i));
        child.parent = node;
      }
    }
  }

  (tree.parent = new TreeNode(null, 0)).children = [tree];
  return tree;
}

// Node-link tree diagram using the Reingold-Tilford "tidy" algorithm
/* harmony default export */ var tree = (function() {
  var separation = tree_defaultSeparation,
      dx = 1,
      dy = 1,
      nodeSize = null;

  function tree(root) {
    var t = treeRoot(root);

    // Compute the layout using Buchheim et al.’s algorithm.
    t.eachAfter(firstWalk), t.parent.m = -t.z;
    t.eachBefore(secondWalk);

    // If a fixed node size is specified, scale x and y.
    if (nodeSize) root.eachBefore(sizeNode);

    // If a fixed tree size is specified, scale x and y based on the extent.
    // Compute the left-most, right-most, and depth-most nodes for extents.
    else {
      var left = root,
          right = root,
          bottom = root;
      root.eachBefore(function(node) {
        if (node.x < left.x) left = node;
        if (node.x > right.x) right = node;
        if (node.depth > bottom.depth) bottom = node;
      });
      var s = left === right ? 1 : separation(left, right) / 2,
          tx = s - left.x,
          kx = dx / (right.x + s + tx),
          ky = dy / (bottom.depth || 1);
      root.eachBefore(function(node) {
        node.x = (node.x + tx) * kx;
        node.y = node.depth * ky;
      });
    }

    return root;
  }

  // Computes a preliminary x-coordinate for v. Before that, FIRST WALK is
  // applied recursively to the children of v, as well as the function
  // APPORTION. After spacing out the children by calling EXECUTE SHIFTS, the
  // node v is placed to the midpoint of its outermost children.
  function firstWalk(v) {
    var children = v.children,
        siblings = v.parent.children,
        w = v.i ? siblings[v.i - 1] : null;
    if (children) {
      executeShifts(v);
      var midpoint = (children[0].z + children[children.length - 1].z) / 2;
      if (w) {
        v.z = w.z + separation(v._, w._);
        v.m = v.z - midpoint;
      } else {
        v.z = midpoint;
      }
    } else if (w) {
      v.z = w.z + separation(v._, w._);
    }
    v.parent.A = apportion(v, w, v.parent.A || siblings[0]);
  }

  // Computes all real x-coordinates by summing up the modifiers recursively.
  function secondWalk(v) {
    v._.x = v.z + v.parent.m;
    v.m += v.parent.m;
  }

  // The core of the algorithm. Here, a new subtree is combined with the
  // previous subtrees. Threads are used to traverse the inside and outside
  // contours of the left and right subtree up to the highest common level. The
  // vertices used for the traversals are vi+, vi-, vo-, and vo+, where the
  // superscript o means outside and i means inside, the subscript - means left
  // subtree and + means right subtree. For summing up the modifiers along the
  // contour, we use respective variables si+, si-, so-, and so+. Whenever two
  // nodes of the inside contours conflict, we compute the left one of the
  // greatest uncommon ancestors using the function ANCESTOR and call MOVE
  // SUBTREE to shift the subtree and prepare the shifts of smaller subtrees.
  // Finally, we add a new thread (if necessary).
  function apportion(v, w, ancestor) {
    if (w) {
      var vip = v,
          vop = v,
          vim = w,
          vom = vip.parent.children[0],
          sip = vip.m,
          sop = vop.m,
          sim = vim.m,
          som = vom.m,
          shift;
      while (vim = nextRight(vim), vip = nextLeft(vip), vim && vip) {
        vom = nextLeft(vom);
        vop = nextRight(vop);
        vop.a = v;
        shift = vim.z + sim - vip.z - sip + separation(vim._, vip._);
        if (shift > 0) {
          moveSubtree(nextAncestor(vim, v, ancestor), v, shift);
          sip += shift;
          sop += shift;
        }
        sim += vim.m;
        sip += vip.m;
        som += vom.m;
        sop += vop.m;
      }
      if (vim && !nextRight(vop)) {
        vop.t = vim;
        vop.m += sim - sop;
      }
      if (vip && !nextLeft(vom)) {
        vom.t = vip;
        vom.m += sip - som;
        ancestor = v;
      }
    }
    return ancestor;
  }

  function sizeNode(node) {
    node.x *= dx;
    node.y = node.depth * dy;
  }

  tree.separation = function(x) {
    return arguments.length ? (separation = x, tree) : separation;
  };

  tree.size = function(x) {
    return arguments.length ? (nodeSize = false, dx = +x[0], dy = +x[1], tree) : (nodeSize ? null : [dx, dy]);
  };

  tree.nodeSize = function(x) {
    return arguments.length ? (nodeSize = true, dx = +x[0], dy = +x[1], tree) : (nodeSize ? [dx, dy] : null);
  };

  return tree;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/treemap/slice.js
/* harmony default export */ var treemap_slice = (function(parent, x0, y0, x1, y1) {
  var nodes = parent.children,
      node,
      i = -1,
      n = nodes.length,
      k = parent.value && (y1 - y0) / parent.value;

  while (++i < n) {
    node = nodes[i], node.x0 = x0, node.x1 = x1;
    node.y0 = y0, node.y1 = y0 += node.value * k;
  }
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/treemap/squarify.js



var phi = (1 + Math.sqrt(5)) / 2;

function squarifyRatio(ratio, parent, x0, y0, x1, y1) {
  var rows = [],
      nodes = parent.children,
      row,
      nodeValue,
      i0 = 0,
      i1 = 0,
      n = nodes.length,
      dx, dy,
      value = parent.value,
      sumValue,
      minValue,
      maxValue,
      newRatio,
      minRatio,
      alpha,
      beta;

  while (i0 < n) {
    dx = x1 - x0, dy = y1 - y0;

    // Find the next non-empty node.
    do sumValue = nodes[i1++].value; while (!sumValue && i1 < n);
    minValue = maxValue = sumValue;
    alpha = Math.max(dy / dx, dx / dy) / (value * ratio);
    beta = sumValue * sumValue * alpha;
    minRatio = Math.max(maxValue / beta, beta / minValue);

    // Keep adding nodes while the aspect ratio maintains or improves.
    for (; i1 < n; ++i1) {
      sumValue += nodeValue = nodes[i1].value;
      if (nodeValue < minValue) minValue = nodeValue;
      if (nodeValue > maxValue) maxValue = nodeValue;
      beta = sumValue * sumValue * alpha;
      newRatio = Math.max(maxValue / beta, beta / minValue);
      if (newRatio > minRatio) { sumValue -= nodeValue; break; }
      minRatio = newRatio;
    }

    // Position and record the row orientation.
    rows.push(row = {value: sumValue, dice: dx < dy, children: nodes.slice(i0, i1)});
    if (row.dice) dice(row, x0, y0, x1, value ? y0 += dy * sumValue / value : y1);
    else treemap_slice(row, x0, y0, value ? x0 += dx * sumValue / value : x1, y1);
    value -= sumValue, i0 = i1;
  }

  return rows;
}

/* harmony default export */ var squarify = ((function custom(ratio) {

  function squarify(parent, x0, y0, x1, y1) {
    squarifyRatio(ratio, parent, x0, y0, x1, y1);
  }

  squarify.ratio = function(x) {
    return custom((x = +x) > 1 ? x : 1);
  };

  return squarify;
})(phi));

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/treemap/index.js





/* harmony default export */ var src_treemap = (function() {
  var tile = squarify,
      round = false,
      dx = 1,
      dy = 1,
      paddingStack = [0],
      paddingInner = constantZero,
      paddingTop = constantZero,
      paddingRight = constantZero,
      paddingBottom = constantZero,
      paddingLeft = constantZero;

  function treemap(root) {
    root.x0 =
    root.y0 = 0;
    root.x1 = dx;
    root.y1 = dy;
    root.eachBefore(positionNode);
    paddingStack = [0];
    if (round) root.eachBefore(treemap_round);
    return root;
  }

  function positionNode(node) {
    var p = paddingStack[node.depth],
        x0 = node.x0 + p,
        y0 = node.y0 + p,
        x1 = node.x1 - p,
        y1 = node.y1 - p;
    if (x1 < x0) x0 = x1 = (x0 + x1) / 2;
    if (y1 < y0) y0 = y1 = (y0 + y1) / 2;
    node.x0 = x0;
    node.y0 = y0;
    node.x1 = x1;
    node.y1 = y1;
    if (node.children) {
      p = paddingStack[node.depth + 1] = paddingInner(node) / 2;
      x0 += paddingLeft(node) - p;
      y0 += paddingTop(node) - p;
      x1 -= paddingRight(node) - p;
      y1 -= paddingBottom(node) - p;
      if (x1 < x0) x0 = x1 = (x0 + x1) / 2;
      if (y1 < y0) y0 = y1 = (y0 + y1) / 2;
      tile(node, x0, y0, x1, y1);
    }
  }

  treemap.round = function(x) {
    return arguments.length ? (round = !!x, treemap) : round;
  };

  treemap.size = function(x) {
    return arguments.length ? (dx = +x[0], dy = +x[1], treemap) : [dx, dy];
  };

  treemap.tile = function(x) {
    return arguments.length ? (tile = required(x), treemap) : tile;
  };

  treemap.padding = function(x) {
    return arguments.length ? treemap.paddingInner(x).paddingOuter(x) : treemap.paddingInner();
  };

  treemap.paddingInner = function(x) {
    return arguments.length ? (paddingInner = typeof x === "function" ? x : src_constant(+x), treemap) : paddingInner;
  };

  treemap.paddingOuter = function(x) {
    return arguments.length ? treemap.paddingTop(x).paddingRight(x).paddingBottom(x).paddingLeft(x) : treemap.paddingTop();
  };

  treemap.paddingTop = function(x) {
    return arguments.length ? (paddingTop = typeof x === "function" ? x : src_constant(+x), treemap) : paddingTop;
  };

  treemap.paddingRight = function(x) {
    return arguments.length ? (paddingRight = typeof x === "function" ? x : src_constant(+x), treemap) : paddingRight;
  };

  treemap.paddingBottom = function(x) {
    return arguments.length ? (paddingBottom = typeof x === "function" ? x : src_constant(+x), treemap) : paddingBottom;
  };

  treemap.paddingLeft = function(x) {
    return arguments.length ? (paddingLeft = typeof x === "function" ? x : src_constant(+x), treemap) : paddingLeft;
  };

  return treemap;
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/treemap/binary.js
/* harmony default export */ var binary = (function(parent, x0, y0, x1, y1) {
  var nodes = parent.children,
      i, n = nodes.length,
      sum, sums = new Array(n + 1);

  for (sums[0] = sum = i = 0; i < n; ++i) {
    sums[i + 1] = sum += nodes[i].value;
  }

  partition(0, n, parent.value, x0, y0, x1, y1);

  function partition(i, j, value, x0, y0, x1, y1) {
    if (i >= j - 1) {
      var node = nodes[i];
      node.x0 = x0, node.y0 = y0;
      node.x1 = x1, node.y1 = y1;
      return;
    }

    var valueOffset = sums[i],
        valueTarget = (value / 2) + valueOffset,
        k = i + 1,
        hi = j - 1;

    while (k < hi) {
      var mid = k + hi >>> 1;
      if (sums[mid] < valueTarget) k = mid + 1;
      else hi = mid;
    }

    if ((valueTarget - sums[k - 1]) < (sums[k] - valueTarget) && i + 1 < k) --k;

    var valueLeft = sums[k] - valueOffset,
        valueRight = value - valueLeft;

    if ((x1 - x0) > (y1 - y0)) {
      var xk = (x0 * valueRight + x1 * valueLeft) / value;
      partition(i, k, valueLeft, x0, y0, xk, y1);
      partition(k, j, valueRight, xk, y0, x1, y1);
    } else {
      var yk = (y0 * valueRight + y1 * valueLeft) / value;
      partition(i, k, valueLeft, x0, y0, x1, yk);
      partition(k, j, valueRight, x0, yk, x1, y1);
    }
  }
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/treemap/sliceDice.js



/* harmony default export */ var sliceDice = (function(parent, x0, y0, x1, y1) {
  (parent.depth & 1 ? treemap_slice : dice)(parent, x0, y0, x1, y1);
});

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/treemap/resquarify.js




/* harmony default export */ var treemap_resquarify = ((function custom(ratio) {

  function resquarify(parent, x0, y0, x1, y1) {
    if ((rows = parent._squarify) && (rows.ratio === ratio)) {
      var rows,
          row,
          nodes,
          i,
          j = -1,
          n,
          m = rows.length,
          value = parent.value;

      while (++j < m) {
        row = rows[j], nodes = row.children;
        for (i = row.value = 0, n = nodes.length; i < n; ++i) row.value += nodes[i].value;
        if (row.dice) dice(row, x0, y0, x1, y0 += (y1 - y0) * row.value / value);
        else treemap_slice(row, x0, y0, x0 += (x1 - x0) * row.value / value, y1);
        value -= row.value;
      }
    } else {
      parent._squarify = rows = squarifyRatio(ratio, parent, x0, y0, x1, y1);
      rows.ratio = ratio;
    }
  }

  resquarify.ratio = function(x) {
    return custom((x = +x) > 1 ? x : 1);
  };

  return resquarify;
})(phi));

// CONCATENATED MODULE: ./node_modules/d3-hierarchy/src/index.js
















// CONCATENATED MODULE: ./node_modules/d3-dispatch/src/dispatch.js
var noop = {value: function() {}};

function dispatch_dispatch() {
  for (var i = 0, n = arguments.length, _ = {}, t; i < n; ++i) {
    if (!(t = arguments[i] + "") || (t in _)) throw new Error("illegal type: " + t);
    _[t] = [];
  }
  return new Dispatch(_);
}

function Dispatch(_) {
  this._ = _;
}

function dispatch_parseTypenames(typenames, types) {
  return typenames.trim().split(/^|\s+/).map(function(t) {
    var name = "", i = t.indexOf(".");
    if (i >= 0) name = t.slice(i + 1), t = t.slice(0, i);
    if (t && !types.hasOwnProperty(t)) throw new Error("unknown type: " + t);
    return {type: t, name: name};
  });
}

Dispatch.prototype = dispatch_dispatch.prototype = {
  constructor: Dispatch,
  on: function(typename, callback) {
    var _ = this._,
        T = dispatch_parseTypenames(typename + "", _),
        t,
        i = -1,
        n = T.length;

    // If no callback was specified, return the callback of the given type and name.
    if (arguments.length < 2) {
      while (++i < n) if ((t = (typename = T[i]).type) && (t = get(_[t], typename.name))) return t;
      return;
    }

    // If a type was specified, set the callback for the given type and name.
    // Otherwise, if a null callback was specified, remove callbacks of the given name.
    if (callback != null && typeof callback !== "function") throw new Error("invalid callback: " + callback);
    while (++i < n) {
      if (t = (typename = T[i]).type) _[t] = set(_[t], typename.name, callback);
      else if (callback == null) for (t in _) _[t] = set(_[t], typename.name, null);
    }

    return this;
  },
  copy: function() {
    var copy = {}, _ = this._;
    for (var t in _) copy[t] = _[t].slice();
    return new Dispatch(copy);
  },
  call: function(type, that) {
    if ((n = arguments.length - 2) > 0) for (var args = new Array(n), i = 0, n, t; i < n; ++i) args[i] = arguments[i + 2];
    if (!this._.hasOwnProperty(type)) throw new Error("unknown type: " + type);
    for (t = this._[type], i = 0, n = t.length; i < n; ++i) t[i].value.apply(that, args);
  },
  apply: function(type, that, args) {
    if (!this._.hasOwnProperty(type)) throw new Error("unknown type: " + type);
    for (var t = this._[type], i = 0, n = t.length; i < n; ++i) t[i].value.apply(that, args);
  }
};

function get(type, name) {
  for (var i = 0, n = type.length, c; i < n; ++i) {
    if ((c = type[i]).name === name) {
      return c.value;
    }
  }
}

function set(type, name, callback) {
  for (var i = 0, n = type.length; i < n; ++i) {
    if (type[i].name === name) {
      type[i] = noop, type = type.slice(0, i).concat(type.slice(i + 1));
      break;
    }
  }
  if (callback != null) type.push({name: name, value: callback});
  return type;
}

/* harmony default export */ var src_dispatch = (dispatch_dispatch);

// CONCATENATED MODULE: ./node_modules/d3-dispatch/src/index.js


// CONCATENATED MODULE: ./node_modules/d3-drag/src/noevent.js


function nopropagation() {
  on_event.stopImmediatePropagation();
}

/* harmony default export */ var noevent = (function() {
  on_event.preventDefault();
  on_event.stopImmediatePropagation();
});

// CONCATENATED MODULE: ./node_modules/d3-drag/src/nodrag.js



/* harmony default export */ var nodrag = (function(view) {
  var root = view.document.documentElement,
      selection = src_select(view).on("dragstart.drag", noevent, true);
  if ("onselectstart" in root) {
    selection.on("selectstart.drag", noevent, true);
  } else {
    root.__noselect = root.style.MozUserSelect;
    root.style.MozUserSelect = "none";
  }
});

function yesdrag(view, noclick) {
  var root = view.document.documentElement,
      selection = src_select(view).on("dragstart.drag", null);
  if (noclick) {
    selection.on("click.drag", noevent, true);
    setTimeout(function() { selection.on("click.drag", null); }, 0);
  }
  if ("onselectstart" in root) {
    selection.on("selectstart.drag", null);
  } else {
    root.style.MozUserSelect = root.__noselect;
    delete root.__noselect;
  }
}

// CONCATENATED MODULE: ./node_modules/d3-drag/src/constant.js
/* harmony default export */ var d3_drag_src_constant = (function(x) {
  return function() {
    return x;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-drag/src/event.js
function DragEvent(target, type, subject, id, active, x, y, dx, dy, dispatch) {
  this.target = target;
  this.type = type;
  this.subject = subject;
  this.identifier = id;
  this.active = active;
  this.x = x;
  this.y = y;
  this.dx = dx;
  this.dy = dy;
  this._ = dispatch;
}

DragEvent.prototype.on = function() {
  var value = this._.on.apply(this._, arguments);
  return value === this._ ? this : value;
};

// CONCATENATED MODULE: ./node_modules/d3-drag/src/drag.js







// Ignore right-click, since that should open the context menu.
function defaultFilter() {
  return !on_event.button;
}

function defaultContainer() {
  return this.parentNode;
}

function defaultSubject(d) {
  return d == null ? {x: on_event.x, y: on_event.y} : d;
}

function defaultTouchable() {
  return "ontouchstart" in this;
}

/* harmony default export */ var src_drag = (function() {
  var filter = defaultFilter,
      container = defaultContainer,
      subject = defaultSubject,
      touchable = defaultTouchable,
      gestures = {},
      listeners = src_dispatch("start", "drag", "end"),
      active = 0,
      mousedownx,
      mousedowny,
      mousemoving,
      touchending,
      clickDistance2 = 0;

  function drag(selection) {
    selection
        .on("mousedown.drag", mousedowned)
      .filter(touchable)
        .on("touchstart.drag", touchstarted)
        .on("touchmove.drag", touchmoved)
        .on("touchend.drag touchcancel.drag", touchended)
        .style("touch-action", "none")
        .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }

  function mousedowned() {
    if (touchending || !filter.apply(this, arguments)) return;
    var gesture = beforestart("mouse", container.apply(this, arguments), mouse, this, arguments);
    if (!gesture) return;
    src_select(on_event.view).on("mousemove.drag", mousemoved, true).on("mouseup.drag", mouseupped, true);
    nodrag(on_event.view);
    nopropagation();
    mousemoving = false;
    mousedownx = on_event.clientX;
    mousedowny = on_event.clientY;
    gesture("start");
  }

  function mousemoved() {
    noevent();
    if (!mousemoving) {
      var dx = on_event.clientX - mousedownx, dy = on_event.clientY - mousedowny;
      mousemoving = dx * dx + dy * dy > clickDistance2;
    }
    gestures.mouse("drag");
  }

  function mouseupped() {
    src_select(on_event.view).on("mousemove.drag mouseup.drag", null);
    yesdrag(on_event.view, mousemoving);
    noevent();
    gestures.mouse("end");
  }

  function touchstarted() {
    if (!filter.apply(this, arguments)) return;
    var touches = on_event.changedTouches,
        c = container.apply(this, arguments),
        n = touches.length, i, gesture;

    for (i = 0; i < n; ++i) {
      if (gesture = beforestart(touches[i].identifier, c, src_touch, this, arguments)) {
        nopropagation();
        gesture("start");
      }
    }
  }

  function touchmoved() {
    var touches = on_event.changedTouches,
        n = touches.length, i, gesture;

    for (i = 0; i < n; ++i) {
      if (gesture = gestures[touches[i].identifier]) {
        noevent();
        gesture("drag");
      }
    }
  }

  function touchended() {
    var touches = on_event.changedTouches,
        n = touches.length, i, gesture;

    if (touchending) clearTimeout(touchending);
    touchending = setTimeout(function() { touchending = null; }, 500); // Ghost clicks are delayed!
    for (i = 0; i < n; ++i) {
      if (gesture = gestures[touches[i].identifier]) {
        nopropagation();
        gesture("end");
      }
    }
  }

  function beforestart(id, container, point, that, args) {
    var p = point(container, id), s, dx, dy,
        sublisteners = listeners.copy();

    if (!customEvent(new DragEvent(drag, "beforestart", s, id, active, p[0], p[1], 0, 0, sublisteners), function() {
      if ((on_event.subject = s = subject.apply(that, args)) == null) return false;
      dx = s.x - p[0] || 0;
      dy = s.y - p[1] || 0;
      return true;
    })) return;

    return function gesture(type) {
      var p0 = p, n;
      switch (type) {
        case "start": gestures[id] = gesture, n = active++; break;
        case "end": delete gestures[id], --active; // nobreak
        case "drag": p = point(container, id), n = active; break;
      }
      customEvent(new DragEvent(drag, type, s, id, n, p[0] + dx, p[1] + dy, p[0] - p0[0], p[1] - p0[1], sublisteners), sublisteners.apply, sublisteners, [type, that, args]);
    };
  }

  drag.filter = function(_) {
    return arguments.length ? (filter = typeof _ === "function" ? _ : d3_drag_src_constant(!!_), drag) : filter;
  };

  drag.container = function(_) {
    return arguments.length ? (container = typeof _ === "function" ? _ : d3_drag_src_constant(_), drag) : container;
  };

  drag.subject = function(_) {
    return arguments.length ? (subject = typeof _ === "function" ? _ : d3_drag_src_constant(_), drag) : subject;
  };

  drag.touchable = function(_) {
    return arguments.length ? (touchable = typeof _ === "function" ? _ : d3_drag_src_constant(!!_), drag) : touchable;
  };

  drag.on = function() {
    var value = listeners.on.apply(listeners, arguments);
    return value === listeners ? drag : value;
  };

  drag.clickDistance = function(_) {
    return arguments.length ? (clickDistance2 = (_ = +_) * _, drag) : Math.sqrt(clickDistance2);
  };

  return drag;
});

// CONCATENATED MODULE: ./node_modules/d3-drag/src/index.js



// CONCATENATED MODULE: ./node_modules/d3-color/src/define.js
/* harmony default export */ var define = (function(constructor, factory, prototype) {
  constructor.prototype = factory.prototype = prototype;
  prototype.constructor = constructor;
});

function extend(parent, definition) {
  var prototype = Object.create(parent.prototype);
  for (var key in definition) prototype[key] = definition[key];
  return prototype;
}

// CONCATENATED MODULE: ./node_modules/d3-color/src/color.js


function Color() {}

var darker = 0.7;
var brighter = 1 / darker;

var reI = "\\s*([+-]?\\d+)\\s*",
    reN = "\\s*([+-]?\\d*\\.?\\d+(?:[eE][+-]?\\d+)?)\\s*",
    reP = "\\s*([+-]?\\d*\\.?\\d+(?:[eE][+-]?\\d+)?)%\\s*",
    reHex3 = /^#([0-9a-f]{3})$/,
    reHex6 = /^#([0-9a-f]{6})$/,
    reRgbInteger = new RegExp("^rgb\\(" + [reI, reI, reI] + "\\)$"),
    reRgbPercent = new RegExp("^rgb\\(" + [reP, reP, reP] + "\\)$"),
    reRgbaInteger = new RegExp("^rgba\\(" + [reI, reI, reI, reN] + "\\)$"),
    reRgbaPercent = new RegExp("^rgba\\(" + [reP, reP, reP, reN] + "\\)$"),
    reHslPercent = new RegExp("^hsl\\(" + [reN, reP, reP] + "\\)$"),
    reHslaPercent = new RegExp("^hsla\\(" + [reN, reP, reP, reN] + "\\)$");

var named = {
  aliceblue: 0xf0f8ff,
  antiquewhite: 0xfaebd7,
  aqua: 0x00ffff,
  aquamarine: 0x7fffd4,
  azure: 0xf0ffff,
  beige: 0xf5f5dc,
  bisque: 0xffe4c4,
  black: 0x000000,
  blanchedalmond: 0xffebcd,
  blue: 0x0000ff,
  blueviolet: 0x8a2be2,
  brown: 0xa52a2a,
  burlywood: 0xdeb887,
  cadetblue: 0x5f9ea0,
  chartreuse: 0x7fff00,
  chocolate: 0xd2691e,
  coral: 0xff7f50,
  cornflowerblue: 0x6495ed,
  cornsilk: 0xfff8dc,
  crimson: 0xdc143c,
  cyan: 0x00ffff,
  darkblue: 0x00008b,
  darkcyan: 0x008b8b,
  darkgoldenrod: 0xb8860b,
  darkgray: 0xa9a9a9,
  darkgreen: 0x006400,
  darkgrey: 0xa9a9a9,
  darkkhaki: 0xbdb76b,
  darkmagenta: 0x8b008b,
  darkolivegreen: 0x556b2f,
  darkorange: 0xff8c00,
  darkorchid: 0x9932cc,
  darkred: 0x8b0000,
  darksalmon: 0xe9967a,
  darkseagreen: 0x8fbc8f,
  darkslateblue: 0x483d8b,
  darkslategray: 0x2f4f4f,
  darkslategrey: 0x2f4f4f,
  darkturquoise: 0x00ced1,
  darkviolet: 0x9400d3,
  deeppink: 0xff1493,
  deepskyblue: 0x00bfff,
  dimgray: 0x696969,
  dimgrey: 0x696969,
  dodgerblue: 0x1e90ff,
  firebrick: 0xb22222,
  floralwhite: 0xfffaf0,
  forestgreen: 0x228b22,
  fuchsia: 0xff00ff,
  gainsboro: 0xdcdcdc,
  ghostwhite: 0xf8f8ff,
  gold: 0xffd700,
  goldenrod: 0xdaa520,
  gray: 0x808080,
  green: 0x008000,
  greenyellow: 0xadff2f,
  grey: 0x808080,
  honeydew: 0xf0fff0,
  hotpink: 0xff69b4,
  indianred: 0xcd5c5c,
  indigo: 0x4b0082,
  ivory: 0xfffff0,
  khaki: 0xf0e68c,
  lavender: 0xe6e6fa,
  lavenderblush: 0xfff0f5,
  lawngreen: 0x7cfc00,
  lemonchiffon: 0xfffacd,
  lightblue: 0xadd8e6,
  lightcoral: 0xf08080,
  lightcyan: 0xe0ffff,
  lightgoldenrodyellow: 0xfafad2,
  lightgray: 0xd3d3d3,
  lightgreen: 0x90ee90,
  lightgrey: 0xd3d3d3,
  lightpink: 0xffb6c1,
  lightsalmon: 0xffa07a,
  lightseagreen: 0x20b2aa,
  lightskyblue: 0x87cefa,
  lightslategray: 0x778899,
  lightslategrey: 0x778899,
  lightsteelblue: 0xb0c4de,
  lightyellow: 0xffffe0,
  lime: 0x00ff00,
  limegreen: 0x32cd32,
  linen: 0xfaf0e6,
  magenta: 0xff00ff,
  maroon: 0x800000,
  mediumaquamarine: 0x66cdaa,
  mediumblue: 0x0000cd,
  mediumorchid: 0xba55d3,
  mediumpurple: 0x9370db,
  mediumseagreen: 0x3cb371,
  mediumslateblue: 0x7b68ee,
  mediumspringgreen: 0x00fa9a,
  mediumturquoise: 0x48d1cc,
  mediumvioletred: 0xc71585,
  midnightblue: 0x191970,
  mintcream: 0xf5fffa,
  mistyrose: 0xffe4e1,
  moccasin: 0xffe4b5,
  navajowhite: 0xffdead,
  navy: 0x000080,
  oldlace: 0xfdf5e6,
  olive: 0x808000,
  olivedrab: 0x6b8e23,
  orange: 0xffa500,
  orangered: 0xff4500,
  orchid: 0xda70d6,
  palegoldenrod: 0xeee8aa,
  palegreen: 0x98fb98,
  paleturquoise: 0xafeeee,
  palevioletred: 0xdb7093,
  papayawhip: 0xffefd5,
  peachpuff: 0xffdab9,
  peru: 0xcd853f,
  pink: 0xffc0cb,
  plum: 0xdda0dd,
  powderblue: 0xb0e0e6,
  purple: 0x800080,
  rebeccapurple: 0x663399,
  red: 0xff0000,
  rosybrown: 0xbc8f8f,
  royalblue: 0x4169e1,
  saddlebrown: 0x8b4513,
  salmon: 0xfa8072,
  sandybrown: 0xf4a460,
  seagreen: 0x2e8b57,
  seashell: 0xfff5ee,
  sienna: 0xa0522d,
  silver: 0xc0c0c0,
  skyblue: 0x87ceeb,
  slateblue: 0x6a5acd,
  slategray: 0x708090,
  slategrey: 0x708090,
  snow: 0xfffafa,
  springgreen: 0x00ff7f,
  steelblue: 0x4682b4,
  tan: 0xd2b48c,
  teal: 0x008080,
  thistle: 0xd8bfd8,
  tomato: 0xff6347,
  turquoise: 0x40e0d0,
  violet: 0xee82ee,
  wheat: 0xf5deb3,
  white: 0xffffff,
  whitesmoke: 0xf5f5f5,
  yellow: 0xffff00,
  yellowgreen: 0x9acd32
};

define(Color, color_color, {
  displayable: function() {
    return this.rgb().displayable();
  },
  hex: function() {
    return this.rgb().hex();
  },
  toString: function() {
    return this.rgb() + "";
  }
});

function color_color(format) {
  var m;
  format = (format + "").trim().toLowerCase();
  return (m = reHex3.exec(format)) ? (m = parseInt(m[1], 16), new Rgb((m >> 8 & 0xf) | (m >> 4 & 0x0f0), (m >> 4 & 0xf) | (m & 0xf0), ((m & 0xf) << 4) | (m & 0xf), 1)) // #f00
      : (m = reHex6.exec(format)) ? rgbn(parseInt(m[1], 16)) // #ff0000
      : (m = reRgbInteger.exec(format)) ? new Rgb(m[1], m[2], m[3], 1) // rgb(255, 0, 0)
      : (m = reRgbPercent.exec(format)) ? new Rgb(m[1] * 255 / 100, m[2] * 255 / 100, m[3] * 255 / 100, 1) // rgb(100%, 0%, 0%)
      : (m = reRgbaInteger.exec(format)) ? rgba(m[1], m[2], m[3], m[4]) // rgba(255, 0, 0, 1)
      : (m = reRgbaPercent.exec(format)) ? rgba(m[1] * 255 / 100, m[2] * 255 / 100, m[3] * 255 / 100, m[4]) // rgb(100%, 0%, 0%, 1)
      : (m = reHslPercent.exec(format)) ? hsla(m[1], m[2] / 100, m[3] / 100, 1) // hsl(120, 50%, 50%)
      : (m = reHslaPercent.exec(format)) ? hsla(m[1], m[2] / 100, m[3] / 100, m[4]) // hsla(120, 50%, 50%, 1)
      : named.hasOwnProperty(format) ? rgbn(named[format])
      : format === "transparent" ? new Rgb(NaN, NaN, NaN, 0)
      : null;
}

function rgbn(n) {
  return new Rgb(n >> 16 & 0xff, n >> 8 & 0xff, n & 0xff, 1);
}

function rgba(r, g, b, a) {
  if (a <= 0) r = g = b = NaN;
  return new Rgb(r, g, b, a);
}

function rgbConvert(o) {
  if (!(o instanceof Color)) o = color_color(o);
  if (!o) return new Rgb;
  o = o.rgb();
  return new Rgb(o.r, o.g, o.b, o.opacity);
}

function color_rgb(r, g, b, opacity) {
  return arguments.length === 1 ? rgbConvert(r) : new Rgb(r, g, b, opacity == null ? 1 : opacity);
}

function Rgb(r, g, b, opacity) {
  this.r = +r;
  this.g = +g;
  this.b = +b;
  this.opacity = +opacity;
}

define(Rgb, color_rgb, extend(Color, {
  brighter: function(k) {
    k = k == null ? brighter : Math.pow(brighter, k);
    return new Rgb(this.r * k, this.g * k, this.b * k, this.opacity);
  },
  darker: function(k) {
    k = k == null ? darker : Math.pow(darker, k);
    return new Rgb(this.r * k, this.g * k, this.b * k, this.opacity);
  },
  rgb: function() {
    return this;
  },
  displayable: function() {
    return (0 <= this.r && this.r <= 255)
        && (0 <= this.g && this.g <= 255)
        && (0 <= this.b && this.b <= 255)
        && (0 <= this.opacity && this.opacity <= 1);
  },
  hex: function() {
    return "#" + hex(this.r) + hex(this.g) + hex(this.b);
  },
  toString: function() {
    var a = this.opacity; a = isNaN(a) ? 1 : Math.max(0, Math.min(1, a));
    return (a === 1 ? "rgb(" : "rgba(")
        + Math.max(0, Math.min(255, Math.round(this.r) || 0)) + ", "
        + Math.max(0, Math.min(255, Math.round(this.g) || 0)) + ", "
        + Math.max(0, Math.min(255, Math.round(this.b) || 0))
        + (a === 1 ? ")" : ", " + a + ")");
  }
}));

function hex(value) {
  value = Math.max(0, Math.min(255, Math.round(value) || 0));
  return (value < 16 ? "0" : "") + value.toString(16);
}

function hsla(h, s, l, a) {
  if (a <= 0) h = s = l = NaN;
  else if (l <= 0 || l >= 1) h = s = NaN;
  else if (s <= 0) h = NaN;
  return new Hsl(h, s, l, a);
}

function hslConvert(o) {
  if (o instanceof Hsl) return new Hsl(o.h, o.s, o.l, o.opacity);
  if (!(o instanceof Color)) o = color_color(o);
  if (!o) return new Hsl;
  if (o instanceof Hsl) return o;
  o = o.rgb();
  var r = o.r / 255,
      g = o.g / 255,
      b = o.b / 255,
      min = Math.min(r, g, b),
      max = Math.max(r, g, b),
      h = NaN,
      s = max - min,
      l = (max + min) / 2;
  if (s) {
    if (r === max) h = (g - b) / s + (g < b) * 6;
    else if (g === max) h = (b - r) / s + 2;
    else h = (r - g) / s + 4;
    s /= l < 0.5 ? max + min : 2 - max - min;
    h *= 60;
  } else {
    s = l > 0 && l < 1 ? 0 : h;
  }
  return new Hsl(h, s, l, o.opacity);
}

function hsl(h, s, l, opacity) {
  return arguments.length === 1 ? hslConvert(h) : new Hsl(h, s, l, opacity == null ? 1 : opacity);
}

function Hsl(h, s, l, opacity) {
  this.h = +h;
  this.s = +s;
  this.l = +l;
  this.opacity = +opacity;
}

define(Hsl, hsl, extend(Color, {
  brighter: function(k) {
    k = k == null ? brighter : Math.pow(brighter, k);
    return new Hsl(this.h, this.s, this.l * k, this.opacity);
  },
  darker: function(k) {
    k = k == null ? darker : Math.pow(darker, k);
    return new Hsl(this.h, this.s, this.l * k, this.opacity);
  },
  rgb: function() {
    var h = this.h % 360 + (this.h < 0) * 360,
        s = isNaN(h) || isNaN(this.s) ? 0 : this.s,
        l = this.l,
        m2 = l + (l < 0.5 ? l : 1 - l) * s,
        m1 = 2 * l - m2;
    return new Rgb(
      hsl2rgb(h >= 240 ? h - 240 : h + 120, m1, m2),
      hsl2rgb(h, m1, m2),
      hsl2rgb(h < 120 ? h + 240 : h - 120, m1, m2),
      this.opacity
    );
  },
  displayable: function() {
    return (0 <= this.s && this.s <= 1 || isNaN(this.s))
        && (0 <= this.l && this.l <= 1)
        && (0 <= this.opacity && this.opacity <= 1);
  }
}));

/* From FvD 13.37, CSS Color Module Level 3 */
function hsl2rgb(h, m1, m2) {
  return (h < 60 ? m1 + (m2 - m1) * h / 60
      : h < 180 ? m2
      : h < 240 ? m1 + (m2 - m1) * (240 - h) / 60
      : m1) * 255;
}

// CONCATENATED MODULE: ./node_modules/d3-color/src/math.js
var deg2rad = Math.PI / 180;
var rad2deg = 180 / Math.PI;

// CONCATENATED MODULE: ./node_modules/d3-color/src/lab.js




// https://beta.observablehq.com/@mbostock/lab-and-rgb
var K = 18,
    Xn = 0.96422,
    Yn = 1,
    Zn = 0.82521,
    lab_t0 = 4 / 29,
    lab_t1 = 6 / 29,
    t2 = 3 * lab_t1 * lab_t1,
    t3 = lab_t1 * lab_t1 * lab_t1;

function labConvert(o) {
  if (o instanceof Lab) return new Lab(o.l, o.a, o.b, o.opacity);
  if (o instanceof Hcl) {
    if (isNaN(o.h)) return new Lab(o.l, 0, 0, o.opacity);
    var h = o.h * deg2rad;
    return new Lab(o.l, Math.cos(h) * o.c, Math.sin(h) * o.c, o.opacity);
  }
  if (!(o instanceof Rgb)) o = rgbConvert(o);
  var r = rgb2lrgb(o.r),
      g = rgb2lrgb(o.g),
      b = rgb2lrgb(o.b),
      y = xyz2lab((0.2225045 * r + 0.7168786 * g + 0.0606169 * b) / Yn), x, z;
  if (r === g && g === b) x = z = y; else {
    x = xyz2lab((0.4360747 * r + 0.3850649 * g + 0.1430804 * b) / Xn);
    z = xyz2lab((0.0139322 * r + 0.0971045 * g + 0.7141733 * b) / Zn);
  }
  return new Lab(116 * y - 16, 500 * (x - y), 200 * (y - z), o.opacity);
}

function gray(l, opacity) {
  return new Lab(l, 0, 0, opacity == null ? 1 : opacity);
}

function lab(l, a, b, opacity) {
  return arguments.length === 1 ? labConvert(l) : new Lab(l, a, b, opacity == null ? 1 : opacity);
}

function Lab(l, a, b, opacity) {
  this.l = +l;
  this.a = +a;
  this.b = +b;
  this.opacity = +opacity;
}

define(Lab, lab, extend(Color, {
  brighter: function(k) {
    return new Lab(this.l + K * (k == null ? 1 : k), this.a, this.b, this.opacity);
  },
  darker: function(k) {
    return new Lab(this.l - K * (k == null ? 1 : k), this.a, this.b, this.opacity);
  },
  rgb: function() {
    var y = (this.l + 16) / 116,
        x = isNaN(this.a) ? y : y + this.a / 500,
        z = isNaN(this.b) ? y : y - this.b / 200;
    x = Xn * lab2xyz(x);
    y = Yn * lab2xyz(y);
    z = Zn * lab2xyz(z);
    return new Rgb(
      lrgb2rgb( 3.1338561 * x - 1.6168667 * y - 0.4906146 * z),
      lrgb2rgb(-0.9787684 * x + 1.9161415 * y + 0.0334540 * z),
      lrgb2rgb( 0.0719453 * x - 0.2289914 * y + 1.4052427 * z),
      this.opacity
    );
  }
}));

function xyz2lab(t) {
  return t > t3 ? Math.pow(t, 1 / 3) : t / t2 + lab_t0;
}

function lab2xyz(t) {
  return t > lab_t1 ? t * t * t : t2 * (t - lab_t0);
}

function lrgb2rgb(x) {
  return 255 * (x <= 0.0031308 ? 12.92 * x : 1.055 * Math.pow(x, 1 / 2.4) - 0.055);
}

function rgb2lrgb(x) {
  return (x /= 255) <= 0.04045 ? x / 12.92 : Math.pow((x + 0.055) / 1.055, 2.4);
}

function hclConvert(o) {
  if (o instanceof Hcl) return new Hcl(o.h, o.c, o.l, o.opacity);
  if (!(o instanceof Lab)) o = labConvert(o);
  if (o.a === 0 && o.b === 0) return new Hcl(NaN, 0, o.l, o.opacity);
  var h = Math.atan2(o.b, o.a) * rad2deg;
  return new Hcl(h < 0 ? h + 360 : h, Math.sqrt(o.a * o.a + o.b * o.b), o.l, o.opacity);
}

function lch(l, c, h, opacity) {
  return arguments.length === 1 ? hclConvert(l) : new Hcl(h, c, l, opacity == null ? 1 : opacity);
}

function hcl(h, c, l, opacity) {
  return arguments.length === 1 ? hclConvert(h) : new Hcl(h, c, l, opacity == null ? 1 : opacity);
}

function Hcl(h, c, l, opacity) {
  this.h = +h;
  this.c = +c;
  this.l = +l;
  this.opacity = +opacity;
}

define(Hcl, hcl, extend(Color, {
  brighter: function(k) {
    return new Hcl(this.h, this.c, this.l + K * (k == null ? 1 : k), this.opacity);
  },
  darker: function(k) {
    return new Hcl(this.h, this.c, this.l - K * (k == null ? 1 : k), this.opacity);
  },
  rgb: function() {
    return labConvert(this).rgb();
  }
}));

// CONCATENATED MODULE: ./node_modules/d3-color/src/cubehelix.js




var A = -0.14861,
    cubehelix_B = +1.78277,
    C = -0.29227,
    cubehelix_D = -0.90649,
    E = +1.97294,
    ED = E * cubehelix_D,
    EB = E * cubehelix_B,
    BC_DA = cubehelix_B * C - cubehelix_D * A;

function cubehelixConvert(o) {
  if (o instanceof Cubehelix) return new Cubehelix(o.h, o.s, o.l, o.opacity);
  if (!(o instanceof Rgb)) o = rgbConvert(o);
  var r = o.r / 255,
      g = o.g / 255,
      b = o.b / 255,
      l = (BC_DA * b + ED * r - EB * g) / (BC_DA + ED - EB),
      bl = b - l,
      k = (E * (g - l) - C * bl) / cubehelix_D,
      s = Math.sqrt(k * k + bl * bl) / (E * l * (1 - l)), // NaN if l=0 or l=1
      h = s ? Math.atan2(k, bl) * rad2deg - 120 : NaN;
  return new Cubehelix(h < 0 ? h + 360 : h, s, l, o.opacity);
}

function cubehelix_cubehelix(h, s, l, opacity) {
  return arguments.length === 1 ? cubehelixConvert(h) : new Cubehelix(h, s, l, opacity == null ? 1 : opacity);
}

function Cubehelix(h, s, l, opacity) {
  this.h = +h;
  this.s = +s;
  this.l = +l;
  this.opacity = +opacity;
}

define(Cubehelix, cubehelix_cubehelix, extend(Color, {
  brighter: function(k) {
    k = k == null ? brighter : Math.pow(brighter, k);
    return new Cubehelix(this.h, this.s, this.l * k, this.opacity);
  },
  darker: function(k) {
    k = k == null ? darker : Math.pow(darker, k);
    return new Cubehelix(this.h, this.s, this.l * k, this.opacity);
  },
  rgb: function() {
    var h = isNaN(this.h) ? 0 : (this.h + 120) * deg2rad,
        l = +this.l,
        a = isNaN(this.s) ? 0 : this.s * l * (1 - l),
        cosh = Math.cos(h),
        sinh = Math.sin(h);
    return new Rgb(
      255 * (l + a * (A * cosh + cubehelix_B * sinh)),
      255 * (l + a * (C * cosh + cubehelix_D * sinh)),
      255 * (l + a * (E * cosh)),
      this.opacity
    );
  }
}));

// CONCATENATED MODULE: ./node_modules/d3-color/src/index.js




// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/basis.js
function basis(t1, v0, v1, v2, v3) {
  var t2 = t1 * t1, t3 = t2 * t1;
  return ((1 - 3 * t1 + 3 * t2 - t3) * v0
      + (4 - 6 * t2 + 3 * t3) * v1
      + (1 + 3 * t1 + 3 * t2 - 3 * t3) * v2
      + t3 * v3) / 6;
}

/* harmony default export */ var src_basis = (function(values) {
  var n = values.length - 1;
  return function(t) {
    var i = t <= 0 ? (t = 0) : t >= 1 ? (t = 1, n - 1) : Math.floor(t * n),
        v1 = values[i],
        v2 = values[i + 1],
        v0 = i > 0 ? values[i - 1] : 2 * v1 - v2,
        v3 = i < n - 1 ? values[i + 2] : 2 * v2 - v1;
    return basis((t - i / n) * n, v0, v1, v2, v3);
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/basisClosed.js


/* harmony default export */ var basisClosed = (function(values) {
  var n = values.length;
  return function(t) {
    var i = Math.floor(((t %= 1) < 0 ? ++t : t) * n),
        v0 = values[(i + n - 1) % n],
        v1 = values[i % n],
        v2 = values[(i + 1) % n],
        v3 = values[(i + 2) % n];
    return basis((t - i / n) * n, v0, v1, v2, v3);
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/constant.js
/* harmony default export */ var d3_interpolate_src_constant = (function(x) {
  return function() {
    return x;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/color.js


function linear(a, d) {
  return function(t) {
    return a + t * d;
  };
}

function exponential(a, b, y) {
  return a = Math.pow(a, y), b = Math.pow(b, y) - a, y = 1 / y, function(t) {
    return Math.pow(a + t * b, y);
  };
}

function color_hue(a, b) {
  var d = b - a;
  return d ? linear(a, d > 180 || d < -180 ? d - 360 * Math.round(d / 360) : d) : d3_interpolate_src_constant(isNaN(a) ? b : a);
}

function gamma(y) {
  return (y = +y) === 1 ? nogamma : function(a, b) {
    return b - a ? exponential(a, b, y) : d3_interpolate_src_constant(isNaN(a) ? b : a);
  };
}

function nogamma(a, b) {
  var d = b - a;
  return d ? linear(a, d) : d3_interpolate_src_constant(isNaN(a) ? b : a);
}

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/rgb.js





/* harmony default export */ var src_rgb = ((function rgbGamma(y) {
  var color = gamma(y);

  function rgb(start, end) {
    var r = color((start = color_rgb(start)).r, (end = color_rgb(end)).r),
        g = color(start.g, end.g),
        b = color(start.b, end.b),
        opacity = nogamma(start.opacity, end.opacity);
    return function(t) {
      start.r = r(t);
      start.g = g(t);
      start.b = b(t);
      start.opacity = opacity(t);
      return start + "";
    };
  }

  rgb.gamma = rgbGamma;

  return rgb;
})(1));

function rgbSpline(spline) {
  return function(colors) {
    var n = colors.length,
        r = new Array(n),
        g = new Array(n),
        b = new Array(n),
        i, color;
    for (i = 0; i < n; ++i) {
      color = color_rgb(colors[i]);
      r[i] = color.r || 0;
      g[i] = color.g || 0;
      b[i] = color.b || 0;
    }
    r = spline(r);
    g = spline(g);
    b = spline(b);
    color.opacity = 1;
    return function(t) {
      color.r = r(t);
      color.g = g(t);
      color.b = b(t);
      return color + "";
    };
  };
}

var rgbBasis = rgbSpline(src_basis);
var rgbBasisClosed = rgbSpline(basisClosed);

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/array.js


/* harmony default export */ var src_array = (function(a, b) {
  var nb = b ? b.length : 0,
      na = a ? Math.min(nb, a.length) : 0,
      x = new Array(na),
      c = new Array(nb),
      i;

  for (i = 0; i < na; ++i) x[i] = src_value(a[i], b[i]);
  for (; i < nb; ++i) c[i] = b[i];

  return function(t) {
    for (i = 0; i < na; ++i) c[i] = x[i](t);
    return c;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/date.js
/* harmony default export */ var date = (function(a, b) {
  var d = new Date;
  return a = +a, b -= a, function(t) {
    return d.setTime(a + b * t), d;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/number.js
/* harmony default export */ var number = (function(a, b) {
  return a = +a, b -= a, function(t) {
    return a + b * t;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/object.js


/* harmony default export */ var object = (function(a, b) {
  var i = {},
      c = {},
      k;

  if (a === null || typeof a !== "object") a = {};
  if (b === null || typeof b !== "object") b = {};

  for (k in b) {
    if (k in a) {
      i[k] = src_value(a[k], b[k]);
    } else {
      c[k] = b[k];
    }
  }

  return function(t) {
    for (k in i) c[k] = i[k](t);
    return c;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/string.js


var reA = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g,
    reB = new RegExp(reA.source, "g");

function zero(b) {
  return function() {
    return b;
  };
}

function one(b) {
  return function(t) {
    return b(t) + "";
  };
}

/* harmony default export */ var string = (function(a, b) {
  var bi = reA.lastIndex = reB.lastIndex = 0, // scan index for next number in b
      am, // current match in a
      bm, // current match in b
      bs, // string preceding current number in b, if any
      i = -1, // index in s
      s = [], // string constants and placeholders
      q = []; // number interpolators

  // Coerce inputs to strings.
  a = a + "", b = b + "";

  // Interpolate pairs of numbers in a & b.
  while ((am = reA.exec(a))
      && (bm = reB.exec(b))) {
    if ((bs = bm.index) > bi) { // a string precedes the next number in b
      bs = b.slice(bi, bs);
      if (s[i]) s[i] += bs; // coalesce with previous string
      else s[++i] = bs;
    }
    if ((am = am[0]) === (bm = bm[0])) { // numbers in a & b match
      if (s[i]) s[i] += bm; // coalesce with previous string
      else s[++i] = bm;
    } else { // interpolate non-matching numbers
      s[++i] = null;
      q.push({i: i, x: number(am, bm)});
    }
    bi = reB.lastIndex;
  }

  // Add remains of b.
  if (bi < b.length) {
    bs = b.slice(bi);
    if (s[i]) s[i] += bs; // coalesce with previous string
    else s[++i] = bs;
  }

  // Special optimization for only a single match.
  // Otherwise, interpolate each of the numbers and rejoin the string.
  return s.length < 2 ? (q[0]
      ? one(q[0].x)
      : zero(b))
      : (b = q.length, function(t) {
          for (var i = 0, o; i < b; ++i) s[(o = q[i]).i] = o.x(t);
          return s.join("");
        });
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/value.js









/* harmony default export */ var src_value = (function(a, b) {
  var t = typeof b, c;
  return b == null || t === "boolean" ? d3_interpolate_src_constant(b)
      : (t === "number" ? number
      : t === "string" ? ((c = color_color(b)) ? (b = c, src_rgb) : string)
      : b instanceof color_color ? src_rgb
      : b instanceof Date ? date
      : Array.isArray(b) ? src_array
      : typeof b.valueOf !== "function" && typeof b.toString !== "function" || isNaN(b) ? object
      : number)(a, b);
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/discrete.js
/* harmony default export */ var discrete = (function(range) {
  var n = range.length;
  return function(t) {
    return range[Math.max(0, Math.min(n - 1, Math.floor(t * n)))];
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/hue.js


/* harmony default export */ var src_hue = (function(a, b) {
  var i = color_hue(+a, +b);
  return function(t) {
    var x = i(t);
    return x - 360 * Math.floor(x / 360);
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/round.js
/* harmony default export */ var src_round = (function(a, b) {
  return a = +a, b -= a, function(t) {
    return Math.round(a + b * t);
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/transform/decompose.js
var degrees = 180 / Math.PI;

var identity = {
  translateX: 0,
  translateY: 0,
  rotate: 0,
  skewX: 0,
  scaleX: 1,
  scaleY: 1
};

/* harmony default export */ var decompose = (function(a, b, c, d, e, f) {
  var scaleX, scaleY, skewX;
  if (scaleX = Math.sqrt(a * a + b * b)) a /= scaleX, b /= scaleX;
  if (skewX = a * c + b * d) c -= a * skewX, d -= b * skewX;
  if (scaleY = Math.sqrt(c * c + d * d)) c /= scaleY, d /= scaleY, skewX /= scaleY;
  if (a * d < b * c) a = -a, b = -b, skewX = -skewX, scaleX = -scaleX;
  return {
    translateX: e,
    translateY: f,
    rotate: Math.atan2(b, a) * degrees,
    skewX: Math.atan(skewX) * degrees,
    scaleX: scaleX,
    scaleY: scaleY
  };
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/transform/parse.js


var cssNode,
    cssRoot,
    cssView,
    svgNode;

function parseCss(value) {
  if (value === "none") return identity;
  if (!cssNode) cssNode = document.createElement("DIV"), cssRoot = document.documentElement, cssView = document.defaultView;
  cssNode.style.transform = value;
  value = cssView.getComputedStyle(cssRoot.appendChild(cssNode), null).getPropertyValue("transform");
  cssRoot.removeChild(cssNode);
  value = value.slice(7, -1).split(",");
  return decompose(+value[0], +value[1], +value[2], +value[3], +value[4], +value[5]);
}

function parseSvg(value) {
  if (value == null) return identity;
  if (!svgNode) svgNode = document.createElementNS("http://www.w3.org/2000/svg", "g");
  svgNode.setAttribute("transform", value);
  if (!(value = svgNode.transform.baseVal.consolidate())) return identity;
  value = value.matrix;
  return decompose(value.a, value.b, value.c, value.d, value.e, value.f);
}

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/transform/index.js



function interpolateTransform(parse, pxComma, pxParen, degParen) {

  function pop(s) {
    return s.length ? s.pop() + " " : "";
  }

  function translate(xa, ya, xb, yb, s, q) {
    if (xa !== xb || ya !== yb) {
      var i = s.push("translate(", null, pxComma, null, pxParen);
      q.push({i: i - 4, x: number(xa, xb)}, {i: i - 2, x: number(ya, yb)});
    } else if (xb || yb) {
      s.push("translate(" + xb + pxComma + yb + pxParen);
    }
  }

  function rotate(a, b, s, q) {
    if (a !== b) {
      if (a - b > 180) b += 360; else if (b - a > 180) a += 360; // shortest path
      q.push({i: s.push(pop(s) + "rotate(", null, degParen) - 2, x: number(a, b)});
    } else if (b) {
      s.push(pop(s) + "rotate(" + b + degParen);
    }
  }

  function skewX(a, b, s, q) {
    if (a !== b) {
      q.push({i: s.push(pop(s) + "skewX(", null, degParen) - 2, x: number(a, b)});
    } else if (b) {
      s.push(pop(s) + "skewX(" + b + degParen);
    }
  }

  function scale(xa, ya, xb, yb, s, q) {
    if (xa !== xb || ya !== yb) {
      var i = s.push(pop(s) + "scale(", null, ",", null, ")");
      q.push({i: i - 4, x: number(xa, xb)}, {i: i - 2, x: number(ya, yb)});
    } else if (xb !== 1 || yb !== 1) {
      s.push(pop(s) + "scale(" + xb + "," + yb + ")");
    }
  }

  return function(a, b) {
    var s = [], // string constants and placeholders
        q = []; // number interpolators
    a = parse(a), b = parse(b);
    translate(a.translateX, a.translateY, b.translateX, b.translateY, s, q);
    rotate(a.rotate, b.rotate, s, q);
    skewX(a.skewX, b.skewX, s, q);
    scale(a.scaleX, a.scaleY, b.scaleX, b.scaleY, s, q);
    a = b = null; // gc
    return function(t) {
      var i = -1, n = q.length, o;
      while (++i < n) s[(o = q[i]).i] = o.x(t);
      return s.join("");
    };
  };
}

var interpolateTransformCss = interpolateTransform(parseCss, "px, ", "px)", "deg)");
var interpolateTransformSvg = interpolateTransform(parseSvg, ", ", ")", ")");

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/zoom.js
var rho = Math.SQRT2,
    rho2 = 2,
    rho4 = 4,
    epsilon2 = 1e-12;

function zoom_cosh(x) {
  return ((x = Math.exp(x)) + 1 / x) / 2;
}

function zoom_sinh(x) {
  return ((x = Math.exp(x)) - 1 / x) / 2;
}

function tanh(x) {
  return ((x = Math.exp(2 * x)) - 1) / (x + 1);
}

// p0 = [ux0, uy0, w0]
// p1 = [ux1, uy1, w1]
/* harmony default export */ var src_zoom = (function(p0, p1) {
  var ux0 = p0[0], uy0 = p0[1], w0 = p0[2],
      ux1 = p1[0], uy1 = p1[1], w1 = p1[2],
      dx = ux1 - ux0,
      dy = uy1 - uy0,
      d2 = dx * dx + dy * dy,
      i,
      S;

  // Special case for u0 ≅ u1.
  if (d2 < epsilon2) {
    S = Math.log(w1 / w0) / rho;
    i = function(t) {
      return [
        ux0 + t * dx,
        uy0 + t * dy,
        w0 * Math.exp(rho * t * S)
      ];
    }
  }

  // General case.
  else {
    var d1 = Math.sqrt(d2),
        b0 = (w1 * w1 - w0 * w0 + rho4 * d2) / (2 * w0 * rho2 * d1),
        b1 = (w1 * w1 - w0 * w0 - rho4 * d2) / (2 * w1 * rho2 * d1),
        r0 = Math.log(Math.sqrt(b0 * b0 + 1) - b0),
        r1 = Math.log(Math.sqrt(b1 * b1 + 1) - b1);
    S = (r1 - r0) / rho;
    i = function(t) {
      var s = t * S,
          coshr0 = zoom_cosh(r0),
          u = w0 / (rho2 * d1) * (coshr0 * tanh(rho * s + r0) - zoom_sinh(r0));
      return [
        ux0 + u * dx,
        uy0 + u * dy,
        w0 * coshr0 / zoom_cosh(rho * s + r0)
      ];
    }
  }

  i.duration = S * 1000;

  return i;
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/hsl.js



function hsl_hsl(hue) {
  return function(start, end) {
    var h = hue((start = hsl(start)).h, (end = hsl(end)).h),
        s = nogamma(start.s, end.s),
        l = nogamma(start.l, end.l),
        opacity = nogamma(start.opacity, end.opacity);
    return function(t) {
      start.h = h(t);
      start.s = s(t);
      start.l = l(t);
      start.opacity = opacity(t);
      return start + "";
    };
  }
}

/* harmony default export */ var src_hsl = (hsl_hsl(color_hue));
var hslLong = hsl_hsl(nogamma);

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/lab.js



function lab_lab(start, end) {
  var l = nogamma((start = lab(start)).l, (end = lab(end)).l),
      a = nogamma(start.a, end.a),
      b = nogamma(start.b, end.b),
      opacity = nogamma(start.opacity, end.opacity);
  return function(t) {
    start.l = l(t);
    start.a = a(t);
    start.b = b(t);
    start.opacity = opacity(t);
    return start + "";
  };
}

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/hcl.js



function hcl_hcl(hue) {
  return function(start, end) {
    var h = hue((start = hcl(start)).h, (end = hcl(end)).h),
        c = nogamma(start.c, end.c),
        l = nogamma(start.l, end.l),
        opacity = nogamma(start.opacity, end.opacity);
    return function(t) {
      start.h = h(t);
      start.c = c(t);
      start.l = l(t);
      start.opacity = opacity(t);
      return start + "";
    };
  }
}

/* harmony default export */ var src_hcl = (hcl_hcl(color_hue));
var hclLong = hcl_hcl(nogamma);

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/cubehelix.js



function src_cubehelix_cubehelix(hue) {
  return (function cubehelixGamma(y) {
    y = +y;

    function cubehelix(start, end) {
      var h = hue((start = cubehelix_cubehelix(start)).h, (end = cubehelix_cubehelix(end)).h),
          s = nogamma(start.s, end.s),
          l = nogamma(start.l, end.l),
          opacity = nogamma(start.opacity, end.opacity);
      return function(t) {
        start.h = h(t);
        start.s = s(t);
        start.l = l(Math.pow(t, y));
        start.opacity = opacity(t);
        return start + "";
      };
    }

    cubehelix.gamma = cubehelixGamma;

    return cubehelix;
  })(1);
}

/* harmony default export */ var src_cubehelix = (src_cubehelix_cubehelix(color_hue));
var cubehelixLong = src_cubehelix_cubehelix(nogamma);

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/piecewise.js
function piecewise(interpolate, values) {
  var i = 0, n = values.length - 1, v = values[0], I = new Array(n < 0 ? 0 : n);
  while (i < n) I[i] = interpolate(v, v = values[++i]);
  return function(t) {
    var i = Math.max(0, Math.min(n - 1, Math.floor(t *= n)));
    return I[i](t - i);
  };
}

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/quantize.js
/* harmony default export */ var quantize = (function(interpolator, n) {
  var samples = new Array(n);
  for (var i = 0; i < n; ++i) samples[i] = interpolator(i / (n - 1));
  return samples;
});

// CONCATENATED MODULE: ./node_modules/d3-interpolate/src/index.js





















// CONCATENATED MODULE: ./node_modules/d3-timer/src/timer.js
var timer_frame = 0, // is an animation frame pending?
    timeout = 0, // is a timeout pending?
    interval = 0, // are any timers active?
    pokeDelay = 1000, // how frequently we check for clock skew
    taskHead,
    taskTail,
    clockLast = 0,
    clockNow = 0,
    clockSkew = 0,
    clock = typeof performance === "object" && performance.now ? performance : Date,
    setFrame = typeof window === "object" && window.requestAnimationFrame ? window.requestAnimationFrame.bind(window) : function(f) { setTimeout(f, 17); };

function now() {
  return clockNow || (setFrame(clearNow), clockNow = clock.now() + clockSkew);
}

function clearNow() {
  clockNow = 0;
}

function Timer() {
  this._call =
  this._time =
  this._next = null;
}

Timer.prototype = timer.prototype = {
  constructor: Timer,
  restart: function(callback, delay, time) {
    if (typeof callback !== "function") throw new TypeError("callback is not a function");
    time = (time == null ? now() : +time) + (delay == null ? 0 : +delay);
    if (!this._next && taskTail !== this) {
      if (taskTail) taskTail._next = this;
      else taskHead = this;
      taskTail = this;
    }
    this._call = callback;
    this._time = time;
    sleep();
  },
  stop: function() {
    if (this._call) {
      this._call = null;
      this._time = Infinity;
      sleep();
    }
  }
};

function timer(callback, delay, time) {
  var t = new Timer;
  t.restart(callback, delay, time);
  return t;
}

function timerFlush() {
  now(); // Get the current time, if not already set.
  ++timer_frame; // Pretend we’ve set an alarm, if we haven’t already.
  var t = taskHead, e;
  while (t) {
    if ((e = clockNow - t._time) >= 0) t._call.call(null, e);
    t = t._next;
  }
  --timer_frame;
}

function wake() {
  clockNow = (clockLast = clock.now()) + clockSkew;
  timer_frame = timeout = 0;
  try {
    timerFlush();
  } finally {
    timer_frame = 0;
    nap();
    clockNow = 0;
  }
}

function poke() {
  var now = clock.now(), delay = now - clockLast;
  if (delay > pokeDelay) clockSkew -= delay, clockLast = now;
}

function nap() {
  var t0, t1 = taskHead, t2, time = Infinity;
  while (t1) {
    if (t1._call) {
      if (time > t1._time) time = t1._time;
      t0 = t1, t1 = t1._next;
    } else {
      t2 = t1._next, t1._next = null;
      t1 = t0 ? t0._next = t2 : taskHead = t2;
    }
  }
  taskTail = t0;
  sleep(time);
}

function sleep(time) {
  if (timer_frame) return; // Soonest alarm already set, or will be.
  if (timeout) timeout = clearTimeout(timeout);
  var delay = time - clockNow; // Strictly less than if we recomputed clockNow.
  if (delay > 24) {
    if (time < Infinity) timeout = setTimeout(wake, time - clock.now() - clockSkew);
    if (interval) interval = clearInterval(interval);
  } else {
    if (!interval) clockLast = clock.now(), interval = setInterval(poke, pokeDelay);
    timer_frame = 1, setFrame(wake);
  }
}

// CONCATENATED MODULE: ./node_modules/d3-timer/src/timeout.js


/* harmony default export */ var src_timeout = (function(callback, delay, time) {
  var t = new Timer;
  delay = delay == null ? 0 : +delay;
  t.restart(function(elapsed) {
    t.stop();
    callback(elapsed + delay);
  }, delay, time);
  return t;
});

// CONCATENATED MODULE: ./node_modules/d3-timer/src/interval.js


/* harmony default export */ var src_interval = (function(callback, delay, time) {
  var t = new Timer, total = delay;
  if (delay == null) return t.restart(callback, delay, time), t;
  delay = +delay, time = time == null ? now() : +time;
  t.restart(function tick(elapsed) {
    elapsed += total;
    t.restart(tick, total += delay, time);
    callback(elapsed);
  }, delay, time);
  return t;
});

// CONCATENATED MODULE: ./node_modules/d3-timer/src/index.js






// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/schedule.js



var emptyOn = src_dispatch("start", "end", "interrupt");
var emptyTween = [];

var CREATED = 0;
var SCHEDULED = 1;
var STARTING = 2;
var STARTED = 3;
var RUNNING = 4;
var ENDING = 5;
var ENDED = 6;

/* harmony default export */ var transition_schedule = (function(node, name, id, index, group, timing) {
  var schedules = node.__transition;
  if (!schedules) node.__transition = {};
  else if (id in schedules) return;
  schedule_create(node, id, {
    name: name,
    index: index, // For context during callback.
    group: group, // For context during callback.
    on: emptyOn,
    tween: emptyTween,
    time: timing.time,
    delay: timing.delay,
    duration: timing.duration,
    ease: timing.ease,
    timer: null,
    state: CREATED
  });
});

function init(node, id) {
  var schedule = schedule_get(node, id);
  if (schedule.state > CREATED) throw new Error("too late; already scheduled");
  return schedule;
}

function schedule_set(node, id) {
  var schedule = schedule_get(node, id);
  if (schedule.state > STARTING) throw new Error("too late; already started");
  return schedule;
}

function schedule_get(node, id) {
  var schedule = node.__transition;
  if (!schedule || !(schedule = schedule[id])) throw new Error("transition not found");
  return schedule;
}

function schedule_create(node, id, self) {
  var schedules = node.__transition,
      tween;

  // Initialize the self timer when the transition is created.
  // Note the actual delay is not known until the first callback!
  schedules[id] = self;
  self.timer = timer(schedule, 0, self.time);

  function schedule(elapsed) {
    self.state = SCHEDULED;
    self.timer.restart(start, self.delay, self.time);

    // If the elapsed delay is less than our first sleep, start immediately.
    if (self.delay <= elapsed) start(elapsed - self.delay);
  }

  function start(elapsed) {
    var i, j, n, o;

    // If the state is not SCHEDULED, then we previously errored on start.
    if (self.state !== SCHEDULED) return stop();

    for (i in schedules) {
      o = schedules[i];
      if (o.name !== self.name) continue;

      // While this element already has a starting transition during this frame,
      // defer starting an interrupting transition until that transition has a
      // chance to tick (and possibly end); see d3/d3-transition#54!
      if (o.state === STARTED) return src_timeout(start);

      // Interrupt the active transition, if any.
      // Dispatch the interrupt event.
      if (o.state === RUNNING) {
        o.state = ENDED;
        o.timer.stop();
        o.on.call("interrupt", node, node.__data__, o.index, o.group);
        delete schedules[i];
      }

      // Cancel any pre-empted transitions. No interrupt event is dispatched
      // because the cancelled transitions never started. Note that this also
      // removes this transition from the pending list!
      else if (+i < id) {
        o.state = ENDED;
        o.timer.stop();
        delete schedules[i];
      }
    }

    // Defer the first tick to end of the current frame; see d3/d3#1576.
    // Note the transition may be canceled after start and before the first tick!
    // Note this must be scheduled before the start event; see d3/d3-transition#16!
    // Assuming this is successful, subsequent callbacks go straight to tick.
    src_timeout(function() {
      if (self.state === STARTED) {
        self.state = RUNNING;
        self.timer.restart(tick, self.delay, self.time);
        tick(elapsed);
      }
    });

    // Dispatch the start event.
    // Note this must be done before the tween are initialized.
    self.state = STARTING;
    self.on.call("start", node, node.__data__, self.index, self.group);
    if (self.state !== STARTING) return; // interrupted
    self.state = STARTED;

    // Initialize the tween, deleting null tween.
    tween = new Array(n = self.tween.length);
    for (i = 0, j = -1; i < n; ++i) {
      if (o = self.tween[i].value.call(node, node.__data__, self.index, self.group)) {
        tween[++j] = o;
      }
    }
    tween.length = j + 1;
  }

  function tick(elapsed) {
    var t = elapsed < self.duration ? self.ease.call(null, elapsed / self.duration) : (self.timer.restart(stop), self.state = ENDING, 1),
        i = -1,
        n = tween.length;

    while (++i < n) {
      tween[i].call(null, t);
    }

    // Dispatch the end event.
    if (self.state === ENDING) {
      self.on.call("end", node, node.__data__, self.index, self.group);
      stop();
    }
  }

  function stop() {
    self.state = ENDED;
    self.timer.stop();
    delete schedules[id];
    for (var i in schedules) return; // eslint-disable-line no-unused-vars
    delete node.__transition;
  }
}

// CONCATENATED MODULE: ./node_modules/d3-transition/src/interrupt.js


/* harmony default export */ var interrupt = (function(node, name) {
  var schedules = node.__transition,
      schedule,
      active,
      empty = true,
      i;

  if (!schedules) return;

  name = name == null ? null : name + "";

  for (i in schedules) {
    if ((schedule = schedules[i]).name !== name) { empty = false; continue; }
    active = schedule.state > STARTING && schedule.state < ENDING;
    schedule.state = ENDED;
    schedule.timer.stop();
    if (active) schedule.on.call("interrupt", node, node.__data__, schedule.index, schedule.group);
    delete schedules[i];
  }

  if (empty) delete node.__transition;
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/selection/interrupt.js


/* harmony default export */ var selection_interrupt = (function(name) {
  return this.each(function() {
    interrupt(this, name);
  });
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/tween.js


function tweenRemove(id, name) {
  var tween0, tween1;
  return function() {
    var schedule = schedule_set(this, id),
        tween = schedule.tween;

    // If this node shared tween with the previous node,
    // just assign the updated shared tween and we’re done!
    // Otherwise, copy-on-write.
    if (tween !== tween0) {
      tween1 = tween0 = tween;
      for (var i = 0, n = tween1.length; i < n; ++i) {
        if (tween1[i].name === name) {
          tween1 = tween1.slice();
          tween1.splice(i, 1);
          break;
        }
      }
    }

    schedule.tween = tween1;
  };
}

function tweenFunction(id, name, value) {
  var tween0, tween1;
  if (typeof value !== "function") throw new Error;
  return function() {
    var schedule = schedule_set(this, id),
        tween = schedule.tween;

    // If this node shared tween with the previous node,
    // just assign the updated shared tween and we’re done!
    // Otherwise, copy-on-write.
    if (tween !== tween0) {
      tween1 = (tween0 = tween).slice();
      for (var t = {name: name, value: value}, i = 0, n = tween1.length; i < n; ++i) {
        if (tween1[i].name === name) {
          tween1[i] = t;
          break;
        }
      }
      if (i === n) tween1.push(t);
    }

    schedule.tween = tween1;
  };
}

/* harmony default export */ var transition_tween = (function(name, value) {
  var id = this._id;

  name += "";

  if (arguments.length < 2) {
    var tween = schedule_get(this.node(), id).tween;
    for (var i = 0, n = tween.length, t; i < n; ++i) {
      if ((t = tween[i]).name === name) {
        return t.value;
      }
    }
    return null;
  }

  return this.each((value == null ? tweenRemove : tweenFunction)(id, name, value));
});

function tweenValue(transition, name, value) {
  var id = transition._id;

  transition.each(function() {
    var schedule = schedule_set(this, id);
    (schedule.value || (schedule.value = {}))[name] = value.apply(this, arguments);
  });

  return function(node) {
    return schedule_get(node, id).value[name];
  };
}

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/interpolate.js



/* harmony default export */ var transition_interpolate = (function(a, b) {
  var c;
  return (typeof b === "number" ? number
      : b instanceof color_color ? src_rgb
      : (c = color_color(b)) ? (b = c, src_rgb)
      : string)(a, b);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/attr.js





function attr_attrRemove(name) {
  return function() {
    this.removeAttribute(name);
  };
}

function attr_attrRemoveNS(fullname) {
  return function() {
    this.removeAttributeNS(fullname.space, fullname.local);
  };
}

function attr_attrConstant(name, interpolate, value1) {
  var value00,
      interpolate0;
  return function() {
    var value0 = this.getAttribute(name);
    return value0 === value1 ? null
        : value0 === value00 ? interpolate0
        : interpolate0 = interpolate(value00 = value0, value1);
  };
}

function attr_attrConstantNS(fullname, interpolate, value1) {
  var value00,
      interpolate0;
  return function() {
    var value0 = this.getAttributeNS(fullname.space, fullname.local);
    return value0 === value1 ? null
        : value0 === value00 ? interpolate0
        : interpolate0 = interpolate(value00 = value0, value1);
  };
}

function attr_attrFunction(name, interpolate, value) {
  var value00,
      value10,
      interpolate0;
  return function() {
    var value0, value1 = value(this);
    if (value1 == null) return void this.removeAttribute(name);
    value0 = this.getAttribute(name);
    return value0 === value1 ? null
        : value0 === value00 && value1 === value10 ? interpolate0
        : interpolate0 = interpolate(value00 = value0, value10 = value1);
  };
}

function attr_attrFunctionNS(fullname, interpolate, value) {
  var value00,
      value10,
      interpolate0;
  return function() {
    var value0, value1 = value(this);
    if (value1 == null) return void this.removeAttributeNS(fullname.space, fullname.local);
    value0 = this.getAttributeNS(fullname.space, fullname.local);
    return value0 === value1 ? null
        : value0 === value00 && value1 === value10 ? interpolate0
        : interpolate0 = interpolate(value00 = value0, value10 = value1);
  };
}

/* harmony default export */ var transition_attr = (function(name, value) {
  var fullname = namespace(name), i = fullname === "transform" ? interpolateTransformSvg : transition_interpolate;
  return this.attrTween(name, typeof value === "function"
      ? (fullname.local ? attr_attrFunctionNS : attr_attrFunction)(fullname, i, tweenValue(this, "attr." + name, value))
      : value == null ? (fullname.local ? attr_attrRemoveNS : attr_attrRemove)(fullname)
      : (fullname.local ? attr_attrConstantNS : attr_attrConstant)(fullname, i, value + ""));
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/attrTween.js


function attrTweenNS(fullname, value) {
  function tween() {
    var node = this, i = value.apply(node, arguments);
    return i && function(t) {
      node.setAttributeNS(fullname.space, fullname.local, i(t));
    };
  }
  tween._value = value;
  return tween;
}

function attrTween(name, value) {
  function tween() {
    var node = this, i = value.apply(node, arguments);
    return i && function(t) {
      node.setAttribute(name, i(t));
    };
  }
  tween._value = value;
  return tween;
}

/* harmony default export */ var transition_attrTween = (function(name, value) {
  var key = "attr." + name;
  if (arguments.length < 2) return (key = this.tween(key)) && key._value;
  if (value == null) return this.tween(key, null);
  if (typeof value !== "function") throw new Error;
  var fullname = namespace(name);
  return this.tween(key, (fullname.local ? attrTweenNS : attrTween)(fullname, value));
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/delay.js


function delayFunction(id, value) {
  return function() {
    init(this, id).delay = +value.apply(this, arguments);
  };
}

function delayConstant(id, value) {
  return value = +value, function() {
    init(this, id).delay = value;
  };
}

/* harmony default export */ var transition_delay = (function(value) {
  var id = this._id;

  return arguments.length
      ? this.each((typeof value === "function"
          ? delayFunction
          : delayConstant)(id, value))
      : schedule_get(this.node(), id).delay;
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/duration.js


function durationFunction(id, value) {
  return function() {
    schedule_set(this, id).duration = +value.apply(this, arguments);
  };
}

function durationConstant(id, value) {
  return value = +value, function() {
    schedule_set(this, id).duration = value;
  };
}

/* harmony default export */ var transition_duration = (function(value) {
  var id = this._id;

  return arguments.length
      ? this.each((typeof value === "function"
          ? durationFunction
          : durationConstant)(id, value))
      : schedule_get(this.node(), id).duration;
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/ease.js


function easeConstant(id, value) {
  if (typeof value !== "function") throw new Error;
  return function() {
    schedule_set(this, id).ease = value;
  };
}

/* harmony default export */ var ease = (function(value) {
  var id = this._id;

  return arguments.length
      ? this.each(easeConstant(id, value))
      : schedule_get(this.node(), id).ease;
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/filter.js



/* harmony default export */ var transition_filter = (function(match) {
  if (typeof match !== "function") match = matcher(match);

  for (var groups = this._groups, m = groups.length, subgroups = new Array(m), j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, subgroup = subgroups[j] = [], node, i = 0; i < n; ++i) {
      if ((node = group[i]) && match.call(node, node.__data__, i, group)) {
        subgroup.push(node);
      }
    }
  }

  return new Transition(subgroups, this._parents, this._name, this._id);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/merge.js


/* harmony default export */ var transition_merge = (function(transition) {
  if (transition._id !== this._id) throw new Error;

  for (var groups0 = this._groups, groups1 = transition._groups, m0 = groups0.length, m1 = groups1.length, m = Math.min(m0, m1), merges = new Array(m0), j = 0; j < m; ++j) {
    for (var group0 = groups0[j], group1 = groups1[j], n = group0.length, merge = merges[j] = new Array(n), node, i = 0; i < n; ++i) {
      if (node = group0[i] || group1[i]) {
        merge[i] = node;
      }
    }
  }

  for (; j < m0; ++j) {
    merges[j] = groups0[j];
  }

  return new Transition(merges, this._parents, this._name, this._id);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/on.js


function on_start(name) {
  return (name + "").trim().split(/^|\s+/).every(function(t) {
    var i = t.indexOf(".");
    if (i >= 0) t = t.slice(0, i);
    return !t || t === "start";
  });
}

function onFunction(id, name, listener) {
  var on0, on1, sit = on_start(name) ? init : schedule_set;
  return function() {
    var schedule = sit(this, id),
        on = schedule.on;

    // If this node shared a dispatch with the previous node,
    // just assign the updated shared dispatch and we’re done!
    // Otherwise, copy-on-write.
    if (on !== on0) (on1 = (on0 = on).copy()).on(name, listener);

    schedule.on = on1;
  };
}

/* harmony default export */ var transition_on = (function(name, listener) {
  var id = this._id;

  return arguments.length < 2
      ? schedule_get(this.node(), id).on.on(name)
      : this.each(onFunction(id, name, listener));
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/remove.js
function removeFunction(id) {
  return function() {
    var parent = this.parentNode;
    for (var i in this.__transition) if (+i !== id) return;
    if (parent) parent.removeChild(this);
  };
}

/* harmony default export */ var transition_remove = (function() {
  return this.on("end.remove", removeFunction(this._id));
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/select.js




/* harmony default export */ var transition_select = (function(select) {
  var name = this._name,
      id = this._id;

  if (typeof select !== "function") select = src_selector(select);

  for (var groups = this._groups, m = groups.length, subgroups = new Array(m), j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, subgroup = subgroups[j] = new Array(n), node, subnode, i = 0; i < n; ++i) {
      if ((node = group[i]) && (subnode = select.call(node, node.__data__, i, group))) {
        if ("__data__" in node) subnode.__data__ = node.__data__;
        subgroup[i] = subnode;
        transition_schedule(subgroup[i], name, id, i, subgroup, schedule_get(node, id));
      }
    }
  }

  return new Transition(subgroups, this._parents, name, id);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/selectAll.js




/* harmony default export */ var transition_selectAll = (function(select) {
  var name = this._name,
      id = this._id;

  if (typeof select !== "function") select = selectorAll(select);

  for (var groups = this._groups, m = groups.length, subgroups = [], parents = [], j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, node, i = 0; i < n; ++i) {
      if (node = group[i]) {
        for (var children = select.call(node, node.__data__, i, group), child, inherit = schedule_get(node, id), k = 0, l = children.length; k < l; ++k) {
          if (child = children[k]) {
            transition_schedule(child, name, id, k, children, inherit);
          }
        }
        subgroups.push(children);
        parents.push(node);
      }
    }
  }

  return new Transition(subgroups, parents, name, id);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/selection.js


var selection_Selection = src_selection.prototype.constructor;

/* harmony default export */ var transition_selection = (function() {
  return new selection_Selection(this._groups, this._parents);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/style.js





function style_styleRemove(name, interpolate) {
  var value00,
      value10,
      interpolate0;
  return function() {
    var value0 = styleValue(this, name),
        value1 = (this.style.removeProperty(name), styleValue(this, name));
    return value0 === value1 ? null
        : value0 === value00 && value1 === value10 ? interpolate0
        : interpolate0 = interpolate(value00 = value0, value10 = value1);
  };
}

function styleRemoveEnd(name) {
  return function() {
    this.style.removeProperty(name);
  };
}

function style_styleConstant(name, interpolate, value1) {
  var value00,
      interpolate0;
  return function() {
    var value0 = styleValue(this, name);
    return value0 === value1 ? null
        : value0 === value00 ? interpolate0
        : interpolate0 = interpolate(value00 = value0, value1);
  };
}

function style_styleFunction(name, interpolate, value) {
  var value00,
      value10,
      interpolate0;
  return function() {
    var value0 = styleValue(this, name),
        value1 = value(this);
    if (value1 == null) value1 = (this.style.removeProperty(name), styleValue(this, name));
    return value0 === value1 ? null
        : value0 === value00 && value1 === value10 ? interpolate0
        : interpolate0 = interpolate(value00 = value0, value10 = value1);
  };
}

/* harmony default export */ var transition_style = (function(name, value, priority) {
  var i = (name += "") === "transform" ? interpolateTransformCss : transition_interpolate;
  return value == null ? this
          .styleTween(name, style_styleRemove(name, i))
          .on("end.style." + name, styleRemoveEnd(name))
      : this.styleTween(name, typeof value === "function"
          ? style_styleFunction(name, i, tweenValue(this, "style." + name, value))
          : style_styleConstant(name, i, value + ""), priority);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/styleTween.js
function styleTween(name, value, priority) {
  function tween() {
    var node = this, i = value.apply(node, arguments);
    return i && function(t) {
      node.style.setProperty(name, i(t), priority);
    };
  }
  tween._value = value;
  return tween;
}

/* harmony default export */ var transition_styleTween = (function(name, value, priority) {
  var key = "style." + (name += "");
  if (arguments.length < 2) return (key = this.tween(key)) && key._value;
  if (value == null) return this.tween(key, null);
  if (typeof value !== "function") throw new Error;
  return this.tween(key, styleTween(name, value, priority == null ? "" : priority));
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/text.js


function text_textConstant(value) {
  return function() {
    this.textContent = value;
  };
}

function text_textFunction(value) {
  return function() {
    var value1 = value(this);
    this.textContent = value1 == null ? "" : value1;
  };
}

/* harmony default export */ var transition_text = (function(value) {
  return this.tween("text", typeof value === "function"
      ? text_textFunction(tweenValue(this, "text", value))
      : text_textConstant(value == null ? "" : value + ""));
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/transition.js



/* harmony default export */ var transition_transition = (function() {
  var name = this._name,
      id0 = this._id,
      id1 = newId();

  for (var groups = this._groups, m = groups.length, j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, node, i = 0; i < n; ++i) {
      if (node = group[i]) {
        var inherit = schedule_get(node, id0);
        transition_schedule(node, name, id1, i, group, {
          time: inherit.time + inherit.delay + inherit.duration,
          delay: 0,
          duration: inherit.duration,
          ease: inherit.ease
        });
      }
    }
  }

  return new Transition(groups, this._parents, name, id1);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/transition/index.js



















var transition_id = 0;

function Transition(groups, parents, name, id) {
  this._groups = groups;
  this._parents = parents;
  this._name = name;
  this._id = id;
}

function src_transition_transition(name) {
  return src_selection().transition(name);
}

function newId() {
  return ++transition_id;
}

var selection_prototype = src_selection.prototype;

Transition.prototype = src_transition_transition.prototype = {
  constructor: Transition,
  select: transition_select,
  selectAll: transition_selectAll,
  filter: transition_filter,
  merge: transition_merge,
  selection: transition_selection,
  transition: transition_transition,
  call: selection_prototype.call,
  nodes: selection_prototype.nodes,
  node: selection_prototype.node,
  size: selection_prototype.size,
  empty: selection_prototype.empty,
  each: selection_prototype.each,
  on: transition_on,
  attr: transition_attr,
  attrTween: transition_attrTween,
  style: transition_style,
  styleTween: transition_styleTween,
  text: transition_text,
  remove: transition_remove,
  tween: transition_tween,
  delay: transition_delay,
  duration: transition_duration,
  ease: ease
};

// CONCATENATED MODULE: ./node_modules/d3-ease/src/linear.js
function linear_linear(t) {
  return +t;
}

// CONCATENATED MODULE: ./node_modules/d3-ease/src/quad.js
function quadIn(t) {
  return t * t;
}

function quadOut(t) {
  return t * (2 - t);
}

function quadInOut(t) {
  return ((t *= 2) <= 1 ? t * t : --t * (2 - t) + 1) / 2;
}

// CONCATENATED MODULE: ./node_modules/d3-ease/src/cubic.js
function cubicIn(t) {
  return t * t * t;
}

function cubicOut(t) {
  return --t * t * t + 1;
}

function cubicInOut(t) {
  return ((t *= 2) <= 1 ? t * t * t : (t -= 2) * t * t + 2) / 2;
}

// CONCATENATED MODULE: ./node_modules/d3-ease/src/poly.js
var exponent = 3;

var polyIn = (function custom(e) {
  e = +e;

  function polyIn(t) {
    return Math.pow(t, e);
  }

  polyIn.exponent = custom;

  return polyIn;
})(exponent);

var polyOut = (function custom(e) {
  e = +e;

  function polyOut(t) {
    return 1 - Math.pow(1 - t, e);
  }

  polyOut.exponent = custom;

  return polyOut;
})(exponent);

var polyInOut = (function custom(e) {
  e = +e;

  function polyInOut(t) {
    return ((t *= 2) <= 1 ? Math.pow(t, e) : 2 - Math.pow(2 - t, e)) / 2;
  }

  polyInOut.exponent = custom;

  return polyInOut;
})(exponent);

// CONCATENATED MODULE: ./node_modules/d3-ease/src/sin.js
var pi = Math.PI,
    halfPi = pi / 2;

function sinIn(t) {
  return 1 - Math.cos(t * halfPi);
}

function sinOut(t) {
  return Math.sin(t * halfPi);
}

function sinInOut(t) {
  return (1 - Math.cos(pi * t)) / 2;
}

// CONCATENATED MODULE: ./node_modules/d3-ease/src/exp.js
function expIn(t) {
  return Math.pow(2, 10 * t - 10);
}

function expOut(t) {
  return 1 - Math.pow(2, -10 * t);
}

function expInOut(t) {
  return ((t *= 2) <= 1 ? Math.pow(2, 10 * t - 10) : 2 - Math.pow(2, 10 - 10 * t)) / 2;
}

// CONCATENATED MODULE: ./node_modules/d3-ease/src/circle.js
function circleIn(t) {
  return 1 - Math.sqrt(1 - t * t);
}

function circleOut(t) {
  return Math.sqrt(1 - --t * t);
}

function circleInOut(t) {
  return ((t *= 2) <= 1 ? 1 - Math.sqrt(1 - t * t) : Math.sqrt(1 - (t -= 2) * t) + 1) / 2;
}

// CONCATENATED MODULE: ./node_modules/d3-ease/src/bounce.js
var b1 = 4 / 11,
    b2 = 6 / 11,
    b3 = 8 / 11,
    b4 = 3 / 4,
    b5 = 9 / 11,
    b6 = 10 / 11,
    b7 = 15 / 16,
    b8 = 21 / 22,
    b9 = 63 / 64,
    b0 = 1 / b1 / b1;

function bounceIn(t) {
  return 1 - bounceOut(1 - t);
}

function bounceOut(t) {
  return (t = +t) < b1 ? b0 * t * t : t < b3 ? b0 * (t -= b2) * t + b4 : t < b6 ? b0 * (t -= b5) * t + b7 : b0 * (t -= b8) * t + b9;
}

function bounceInOut(t) {
  return ((t *= 2) <= 1 ? 1 - bounceOut(1 - t) : bounceOut(t - 1) + 1) / 2;
}

// CONCATENATED MODULE: ./node_modules/d3-ease/src/back.js
var overshoot = 1.70158;

var backIn = (function custom(s) {
  s = +s;

  function backIn(t) {
    return t * t * ((s + 1) * t - s);
  }

  backIn.overshoot = custom;

  return backIn;
})(overshoot);

var backOut = (function custom(s) {
  s = +s;

  function backOut(t) {
    return --t * t * ((s + 1) * t + s) + 1;
  }

  backOut.overshoot = custom;

  return backOut;
})(overshoot);

var backInOut = (function custom(s) {
  s = +s;

  function backInOut(t) {
    return ((t *= 2) < 1 ? t * t * ((s + 1) * t - s) : (t -= 2) * t * ((s + 1) * t + s) + 2) / 2;
  }

  backInOut.overshoot = custom;

  return backInOut;
})(overshoot);

// CONCATENATED MODULE: ./node_modules/d3-ease/src/elastic.js
var tau = 2 * Math.PI,
    amplitude = 1,
    period = 0.3;

var elasticIn = (function custom(a, p) {
  var s = Math.asin(1 / (a = Math.max(1, a))) * (p /= tau);

  function elasticIn(t) {
    return a * Math.pow(2, 10 * --t) * Math.sin((s - t) / p);
  }

  elasticIn.amplitude = function(a) { return custom(a, p * tau); };
  elasticIn.period = function(p) { return custom(a, p); };

  return elasticIn;
})(amplitude, period);

var elasticOut = (function custom(a, p) {
  var s = Math.asin(1 / (a = Math.max(1, a))) * (p /= tau);

  function elasticOut(t) {
    return 1 - a * Math.pow(2, -10 * (t = +t)) * Math.sin((t + s) / p);
  }

  elasticOut.amplitude = function(a) { return custom(a, p * tau); };
  elasticOut.period = function(p) { return custom(a, p); };

  return elasticOut;
})(amplitude, period);

var elasticInOut = (function custom(a, p) {
  var s = Math.asin(1 / (a = Math.max(1, a))) * (p /= tau);

  function elasticInOut(t) {
    return ((t = t * 2 - 1) < 0
        ? a * Math.pow(2, 10 * t) * Math.sin((s - t) / p)
        : 2 - a * Math.pow(2, -10 * t) * Math.sin((s + t) / p)) / 2;
  }

  elasticInOut.amplitude = function(a) { return custom(a, p * tau); };
  elasticInOut.period = function(p) { return custom(a, p); };

  return elasticInOut;
})(amplitude, period);

// CONCATENATED MODULE: ./node_modules/d3-ease/src/index.js




















// CONCATENATED MODULE: ./node_modules/d3-transition/src/selection/transition.js





var defaultTiming = {
  time: null, // Set on use.
  delay: 0,
  duration: 250,
  ease: cubicInOut
};

function transition_inherit(node, id) {
  var timing;
  while (!(timing = node.__transition) || !(timing = timing[id])) {
    if (!(node = node.parentNode)) {
      return defaultTiming.time = now(), defaultTiming;
    }
  }
  return timing;
}

/* harmony default export */ var selection_transition = (function(name) {
  var id,
      timing;

  if (name instanceof Transition) {
    id = name._id, name = name._name;
  } else {
    id = newId(), (timing = defaultTiming).time = now(), name = name == null ? null : name + "";
  }

  for (var groups = this._groups, m = groups.length, j = 0; j < m; ++j) {
    for (var group = groups[j], n = group.length, node, i = 0; i < n; ++i) {
      if (node = group[i]) {
        transition_schedule(node, name, id, i, group, timing || transition_inherit(node, id));
      }
    }
  }

  return new Transition(groups, this._parents, name, id);
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/selection/index.js




src_selection.prototype.interrupt = selection_interrupt;
src_selection.prototype.transition = selection_transition;

// CONCATENATED MODULE: ./node_modules/d3-transition/src/active.js



var active_root = [null];

/* harmony default export */ var src_active = (function(node, name) {
  var schedules = node.__transition,
      schedule,
      i;

  if (schedules) {
    name = name == null ? null : name + "";
    for (i in schedules) {
      if ((schedule = schedules[i]).state > SCHEDULED && schedule.name === name) {
        return new Transition([[node]], active_root, name, +i);
      }
    }
  }

  return null;
});

// CONCATENATED MODULE: ./node_modules/d3-transition/src/index.js





// CONCATENATED MODULE: ./node_modules/d3-zoom/src/constant.js
/* harmony default export */ var d3_zoom_src_constant = (function(x) {
  return function() {
    return x;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-zoom/src/event.js
function ZoomEvent(target, type, transform) {
  this.target = target;
  this.type = type;
  this.transform = transform;
}

// CONCATENATED MODULE: ./node_modules/d3-zoom/src/transform.js
function Transform(k, x, y) {
  this.k = k;
  this.x = x;
  this.y = y;
}

Transform.prototype = {
  constructor: Transform,
  scale: function(k) {
    return k === 1 ? this : new Transform(this.k * k, this.x, this.y);
  },
  translate: function(x, y) {
    return x === 0 & y === 0 ? this : new Transform(this.k, this.x + this.k * x, this.y + this.k * y);
  },
  apply: function(point) {
    return [point[0] * this.k + this.x, point[1] * this.k + this.y];
  },
  applyX: function(x) {
    return x * this.k + this.x;
  },
  applyY: function(y) {
    return y * this.k + this.y;
  },
  invert: function(location) {
    return [(location[0] - this.x) / this.k, (location[1] - this.y) / this.k];
  },
  invertX: function(x) {
    return (x - this.x) / this.k;
  },
  invertY: function(y) {
    return (y - this.y) / this.k;
  },
  rescaleX: function(x) {
    return x.copy().domain(x.range().map(this.invertX, this).map(x.invert, x));
  },
  rescaleY: function(y) {
    return y.copy().domain(y.range().map(this.invertY, this).map(y.invert, y));
  },
  toString: function() {
    return "translate(" + this.x + "," + this.y + ") scale(" + this.k + ")";
  }
};

var transform_identity = new Transform(1, 0, 0);

transform_transform.prototype = Transform.prototype;

function transform_transform(node) {
  return node.__zoom || transform_identity;
}

// CONCATENATED MODULE: ./node_modules/d3-zoom/src/noevent.js


function noevent_nopropagation() {
  on_event.stopImmediatePropagation();
}

/* harmony default export */ var src_noevent = (function() {
  on_event.preventDefault();
  on_event.stopImmediatePropagation();
});

// CONCATENATED MODULE: ./node_modules/d3-zoom/src/zoom.js










// Ignore right-click, since that should open the context menu.
function zoom_defaultFilter() {
  return !on_event.button;
}

function defaultExtent() {
  var e = this, w, h;
  if (e instanceof SVGElement) {
    e = e.ownerSVGElement || e;
    w = e.width.baseVal.value;
    h = e.height.baseVal.value;
  } else {
    w = e.clientWidth;
    h = e.clientHeight;
  }
  return [[0, 0], [w, h]];
}

function defaultTransform() {
  return this.__zoom || transform_identity;
}

function defaultWheelDelta() {
  return -on_event.deltaY * (on_event.deltaMode ? 120 : 1) / 500;
}

function zoom_defaultTouchable() {
  return "ontouchstart" in this;
}

function defaultConstrain(transform, extent, translateExtent) {
  var dx0 = transform.invertX(extent[0][0]) - translateExtent[0][0],
      dx1 = transform.invertX(extent[1][0]) - translateExtent[1][0],
      dy0 = transform.invertY(extent[0][1]) - translateExtent[0][1],
      dy1 = transform.invertY(extent[1][1]) - translateExtent[1][1];
  return transform.translate(
    dx1 > dx0 ? (dx0 + dx1) / 2 : Math.min(0, dx0) || Math.max(0, dx1),
    dy1 > dy0 ? (dy0 + dy1) / 2 : Math.min(0, dy0) || Math.max(0, dy1)
  );
}

/* harmony default export */ var d3_zoom_src_zoom = (function() {
  var filter = zoom_defaultFilter,
      extent = defaultExtent,
      constrain = defaultConstrain,
      wheelDelta = defaultWheelDelta,
      touchable = zoom_defaultTouchable,
      scaleExtent = [0, Infinity],
      translateExtent = [[-Infinity, -Infinity], [Infinity, Infinity]],
      duration = 250,
      interpolate = src_zoom,
      gestures = [],
      listeners = src_dispatch("start", "zoom", "end"),
      touchstarting,
      touchending,
      touchDelay = 500,
      wheelDelay = 150,
      clickDistance2 = 0;

  function zoom(selection) {
    selection
        .property("__zoom", defaultTransform)
        .on("wheel.zoom", wheeled)
        .on("mousedown.zoom", mousedowned)
        .on("dblclick.zoom", dblclicked)
      .filter(touchable)
        .on("touchstart.zoom", touchstarted)
        .on("touchmove.zoom", touchmoved)
        .on("touchend.zoom touchcancel.zoom", touchended)
        .style("touch-action", "none")
        .style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
  }

  zoom.transform = function(collection, transform) {
    var selection = collection.selection ? collection.selection() : collection;
    selection.property("__zoom", defaultTransform);
    if (collection !== selection) {
      schedule(collection, transform);
    } else {
      selection.interrupt().each(function() {
        gesture(this, arguments)
            .start()
            .zoom(null, typeof transform === "function" ? transform.apply(this, arguments) : transform)
            .end();
      });
    }
  };

  zoom.scaleBy = function(selection, k) {
    zoom.scaleTo(selection, function() {
      var k0 = this.__zoom.k,
          k1 = typeof k === "function" ? k.apply(this, arguments) : k;
      return k0 * k1;
    });
  };

  zoom.scaleTo = function(selection, k) {
    zoom.transform(selection, function() {
      var e = extent.apply(this, arguments),
          t0 = this.__zoom,
          p0 = centroid(e),
          p1 = t0.invert(p0),
          k1 = typeof k === "function" ? k.apply(this, arguments) : k;
      return constrain(translate(scale(t0, k1), p0, p1), e, translateExtent);
    });
  };

  zoom.translateBy = function(selection, x, y) {
    zoom.transform(selection, function() {
      return constrain(this.__zoom.translate(
        typeof x === "function" ? x.apply(this, arguments) : x,
        typeof y === "function" ? y.apply(this, arguments) : y
      ), extent.apply(this, arguments), translateExtent);
    });
  };

  zoom.translateTo = function(selection, x, y) {
    zoom.transform(selection, function() {
      var e = extent.apply(this, arguments),
          t = this.__zoom,
          p = centroid(e);
      return constrain(transform_identity.translate(p[0], p[1]).scale(t.k).translate(
        typeof x === "function" ? -x.apply(this, arguments) : -x,
        typeof y === "function" ? -y.apply(this, arguments) : -y
      ), e, translateExtent);
    });
  };

  function scale(transform, k) {
    k = Math.max(scaleExtent[0], Math.min(scaleExtent[1], k));
    return k === transform.k ? transform : new Transform(k, transform.x, transform.y);
  }

  function translate(transform, p0, p1) {
    var x = p0[0] - p1[0] * transform.k, y = p0[1] - p1[1] * transform.k;
    return x === transform.x && y === transform.y ? transform : new Transform(transform.k, x, y);
  }

  function centroid(extent) {
    return [(+extent[0][0] + +extent[1][0]) / 2, (+extent[0][1] + +extent[1][1]) / 2];
  }

  function schedule(transition, transform, center) {
    transition
        .on("start.zoom", function() { gesture(this, arguments).start(); })
        .on("interrupt.zoom end.zoom", function() { gesture(this, arguments).end(); })
        .tween("zoom", function() {
          var that = this,
              args = arguments,
              g = gesture(that, args),
              e = extent.apply(that, args),
              p = center || centroid(e),
              w = Math.max(e[1][0] - e[0][0], e[1][1] - e[0][1]),
              a = that.__zoom,
              b = typeof transform === "function" ? transform.apply(that, args) : transform,
              i = interpolate(a.invert(p).concat(w / a.k), b.invert(p).concat(w / b.k));
          return function(t) {
            if (t === 1) t = b; // Avoid rounding error on end.
            else { var l = i(t), k = w / l[2]; t = new Transform(k, p[0] - l[0] * k, p[1] - l[1] * k); }
            g.zoom(null, t);
          };
        });
  }

  function gesture(that, args) {
    for (var i = 0, n = gestures.length, g; i < n; ++i) {
      if ((g = gestures[i]).that === that) {
        return g;
      }
    }
    return new Gesture(that, args);
  }

  function Gesture(that, args) {
    this.that = that;
    this.args = args;
    this.index = -1;
    this.active = 0;
    this.extent = extent.apply(that, args);
  }

  Gesture.prototype = {
    start: function() {
      if (++this.active === 1) {
        this.index = gestures.push(this) - 1;
        this.emit("start");
      }
      return this;
    },
    zoom: function(key, transform) {
      if (this.mouse && key !== "mouse") this.mouse[1] = transform.invert(this.mouse[0]);
      if (this.touch0 && key !== "touch") this.touch0[1] = transform.invert(this.touch0[0]);
      if (this.touch1 && key !== "touch") this.touch1[1] = transform.invert(this.touch1[0]);
      this.that.__zoom = transform;
      this.emit("zoom");
      return this;
    },
    end: function() {
      if (--this.active === 0) {
        gestures.splice(this.index, 1);
        this.index = -1;
        this.emit("end");
      }
      return this;
    },
    emit: function(type) {
      customEvent(new ZoomEvent(zoom, type, this.that.__zoom), listeners.apply, listeners, [type, this.that, this.args]);
    }
  };

  function wheeled() {
    if (!filter.apply(this, arguments)) return;
    var g = gesture(this, arguments),
        t = this.__zoom,
        k = Math.max(scaleExtent[0], Math.min(scaleExtent[1], t.k * Math.pow(2, wheelDelta.apply(this, arguments)))),
        p = mouse(this);

    // If the mouse is in the same location as before, reuse it.
    // If there were recent wheel events, reset the wheel idle timeout.
    if (g.wheel) {
      if (g.mouse[0][0] !== p[0] || g.mouse[0][1] !== p[1]) {
        g.mouse[1] = t.invert(g.mouse[0] = p);
      }
      clearTimeout(g.wheel);
    }

    // If this wheel event won’t trigger a transform change, ignore it.
    else if (t.k === k) return;

    // Otherwise, capture the mouse point and location at the start.
    else {
      g.mouse = [p, t.invert(p)];
      interrupt(this);
      g.start();
    }

    src_noevent();
    g.wheel = setTimeout(wheelidled, wheelDelay);
    g.zoom("mouse", constrain(translate(scale(t, k), g.mouse[0], g.mouse[1]), g.extent, translateExtent));

    function wheelidled() {
      g.wheel = null;
      g.end();
    }
  }

  function mousedowned() {
    if (touchending || !filter.apply(this, arguments)) return;
    var g = gesture(this, arguments),
        v = src_select(on_event.view).on("mousemove.zoom", mousemoved, true).on("mouseup.zoom", mouseupped, true),
        p = mouse(this),
        x0 = on_event.clientX,
        y0 = on_event.clientY;

    nodrag(on_event.view);
    noevent_nopropagation();
    g.mouse = [p, this.__zoom.invert(p)];
    interrupt(this);
    g.start();

    function mousemoved() {
      src_noevent();
      if (!g.moved) {
        var dx = on_event.clientX - x0, dy = on_event.clientY - y0;
        g.moved = dx * dx + dy * dy > clickDistance2;
      }
      g.zoom("mouse", constrain(translate(g.that.__zoom, g.mouse[0] = mouse(g.that), g.mouse[1]), g.extent, translateExtent));
    }

    function mouseupped() {
      v.on("mousemove.zoom mouseup.zoom", null);
      yesdrag(on_event.view, g.moved);
      src_noevent();
      g.end();
    }
  }

  function dblclicked() {
    if (!filter.apply(this, arguments)) return;
    var t0 = this.__zoom,
        p0 = mouse(this),
        p1 = t0.invert(p0),
        k1 = t0.k * (on_event.shiftKey ? 0.5 : 2),
        t1 = constrain(translate(scale(t0, k1), p0, p1), extent.apply(this, arguments), translateExtent);

    src_noevent();
    if (duration > 0) src_select(this).transition().duration(duration).call(schedule, t1, p0);
    else src_select(this).call(zoom.transform, t1);
  }

  function touchstarted() {
    if (!filter.apply(this, arguments)) return;
    var g = gesture(this, arguments),
        touches = on_event.changedTouches,
        started,
        n = touches.length, i, t, p;

    noevent_nopropagation();
    for (i = 0; i < n; ++i) {
      t = touches[i], p = src_touch(this, touches, t.identifier);
      p = [p, this.__zoom.invert(p), t.identifier];
      if (!g.touch0) g.touch0 = p, started = true;
      else if (!g.touch1) g.touch1 = p;
    }

    // If this is a dbltap, reroute to the (optional) dblclick.zoom handler.
    if (touchstarting) {
      touchstarting = clearTimeout(touchstarting);
      if (!g.touch1) {
        g.end();
        p = src_select(this).on("dblclick.zoom");
        if (p) p.apply(this, arguments);
        return;
      }
    }

    if (started) {
      touchstarting = setTimeout(function() { touchstarting = null; }, touchDelay);
      interrupt(this);
      g.start();
    }
  }

  function touchmoved() {
    var g = gesture(this, arguments),
        touches = on_event.changedTouches,
        n = touches.length, i, t, p, l;

    src_noevent();
    if (touchstarting) touchstarting = clearTimeout(touchstarting);
    for (i = 0; i < n; ++i) {
      t = touches[i], p = src_touch(this, touches, t.identifier);
      if (g.touch0 && g.touch0[2] === t.identifier) g.touch0[0] = p;
      else if (g.touch1 && g.touch1[2] === t.identifier) g.touch1[0] = p;
    }
    t = g.that.__zoom;
    if (g.touch1) {
      var p0 = g.touch0[0], l0 = g.touch0[1],
          p1 = g.touch1[0], l1 = g.touch1[1],
          dp = (dp = p1[0] - p0[0]) * dp + (dp = p1[1] - p0[1]) * dp,
          dl = (dl = l1[0] - l0[0]) * dl + (dl = l1[1] - l0[1]) * dl;
      t = scale(t, Math.sqrt(dp / dl));
      p = [(p0[0] + p1[0]) / 2, (p0[1] + p1[1]) / 2];
      l = [(l0[0] + l1[0]) / 2, (l0[1] + l1[1]) / 2];
    }
    else if (g.touch0) p = g.touch0[0], l = g.touch0[1];
    else return;
    g.zoom("touch", constrain(translate(t, p, l), g.extent, translateExtent));
  }

  function touchended() {
    var g = gesture(this, arguments),
        touches = on_event.changedTouches,
        n = touches.length, i, t;

    noevent_nopropagation();
    if (touchending) clearTimeout(touchending);
    touchending = setTimeout(function() { touchending = null; }, touchDelay);
    for (i = 0; i < n; ++i) {
      t = touches[i];
      if (g.touch0 && g.touch0[2] === t.identifier) delete g.touch0;
      else if (g.touch1 && g.touch1[2] === t.identifier) delete g.touch1;
    }
    if (g.touch1 && !g.touch0) g.touch0 = g.touch1, delete g.touch1;
    if (g.touch0) g.touch0[1] = this.__zoom.invert(g.touch0[0]);
    else g.end();
  }

  zoom.wheelDelta = function(_) {
    return arguments.length ? (wheelDelta = typeof _ === "function" ? _ : d3_zoom_src_constant(+_), zoom) : wheelDelta;
  };

  zoom.filter = function(_) {
    return arguments.length ? (filter = typeof _ === "function" ? _ : d3_zoom_src_constant(!!_), zoom) : filter;
  };

  zoom.touchable = function(_) {
    return arguments.length ? (touchable = typeof _ === "function" ? _ : d3_zoom_src_constant(!!_), zoom) : touchable;
  };

  zoom.extent = function(_) {
    return arguments.length ? (extent = typeof _ === "function" ? _ : d3_zoom_src_constant([[+_[0][0], +_[0][1]], [+_[1][0], +_[1][1]]]), zoom) : extent;
  };

  zoom.scaleExtent = function(_) {
    return arguments.length ? (scaleExtent[0] = +_[0], scaleExtent[1] = +_[1], zoom) : [scaleExtent[0], scaleExtent[1]];
  };

  zoom.translateExtent = function(_) {
    return arguments.length ? (translateExtent[0][0] = +_[0][0], translateExtent[1][0] = +_[1][0], translateExtent[0][1] = +_[0][1], translateExtent[1][1] = +_[1][1], zoom) : [[translateExtent[0][0], translateExtent[0][1]], [translateExtent[1][0], translateExtent[1][1]]];
  };

  zoom.constrain = function(_) {
    return arguments.length ? (constrain = _, zoom) : constrain;
  };

  zoom.duration = function(_) {
    return arguments.length ? (duration = +_, zoom) : duration;
  };

  zoom.interpolate = function(_) {
    return arguments.length ? (interpolate = _, zoom) : interpolate;
  };

  zoom.on = function() {
    var value = listeners.on.apply(listeners, arguments);
    return value === listeners ? zoom : value;
  };

  zoom.clickDistance = function(_) {
    return arguments.length ? (clickDistance2 = (_ = +_) * _, zoom) : Math.sqrt(clickDistance2);
  };

  return zoom;
});

// CONCATENATED MODULE: ./node_modules/d3-zoom/src/index.js



// CONCATENATED MODULE: ./node_modules/d3-path/src/path.js
var path_pi = Math.PI,
    path_tau = 2 * path_pi,
    epsilon = 1e-6,
    tauEpsilon = path_tau - epsilon;

function Path() {
  this._x0 = this._y0 = // start of current subpath
  this._x1 = this._y1 = null; // end of current subpath
  this._ = "";
}

function path_path() {
  return new Path;
}

Path.prototype = path_path.prototype = {
  constructor: Path,
  moveTo: function(x, y) {
    this._ += "M" + (this._x0 = this._x1 = +x) + "," + (this._y0 = this._y1 = +y);
  },
  closePath: function() {
    if (this._x1 !== null) {
      this._x1 = this._x0, this._y1 = this._y0;
      this._ += "Z";
    }
  },
  lineTo: function(x, y) {
    this._ += "L" + (this._x1 = +x) + "," + (this._y1 = +y);
  },
  quadraticCurveTo: function(x1, y1, x, y) {
    this._ += "Q" + (+x1) + "," + (+y1) + "," + (this._x1 = +x) + "," + (this._y1 = +y);
  },
  bezierCurveTo: function(x1, y1, x2, y2, x, y) {
    this._ += "C" + (+x1) + "," + (+y1) + "," + (+x2) + "," + (+y2) + "," + (this._x1 = +x) + "," + (this._y1 = +y);
  },
  arcTo: function(x1, y1, x2, y2, r) {
    x1 = +x1, y1 = +y1, x2 = +x2, y2 = +y2, r = +r;
    var x0 = this._x1,
        y0 = this._y1,
        x21 = x2 - x1,
        y21 = y2 - y1,
        x01 = x0 - x1,
        y01 = y0 - y1,
        l01_2 = x01 * x01 + y01 * y01;

    // Is the radius negative? Error.
    if (r < 0) throw new Error("negative radius: " + r);

    // Is this path empty? Move to (x1,y1).
    if (this._x1 === null) {
      this._ += "M" + (this._x1 = x1) + "," + (this._y1 = y1);
    }

    // Or, is (x1,y1) coincident with (x0,y0)? Do nothing.
    else if (!(l01_2 > epsilon));

    // Or, are (x0,y0), (x1,y1) and (x2,y2) collinear?
    // Equivalently, is (x1,y1) coincident with (x2,y2)?
    // Or, is the radius zero? Line to (x1,y1).
    else if (!(Math.abs(y01 * x21 - y21 * x01) > epsilon) || !r) {
      this._ += "L" + (this._x1 = x1) + "," + (this._y1 = y1);
    }

    // Otherwise, draw an arc!
    else {
      var x20 = x2 - x0,
          y20 = y2 - y0,
          l21_2 = x21 * x21 + y21 * y21,
          l20_2 = x20 * x20 + y20 * y20,
          l21 = Math.sqrt(l21_2),
          l01 = Math.sqrt(l01_2),
          l = r * Math.tan((path_pi - Math.acos((l21_2 + l01_2 - l20_2) / (2 * l21 * l01))) / 2),
          t01 = l / l01,
          t21 = l / l21;

      // If the start tangent is not coincident with (x0,y0), line to.
      if (Math.abs(t01 - 1) > epsilon) {
        this._ += "L" + (x1 + t01 * x01) + "," + (y1 + t01 * y01);
      }

      this._ += "A" + r + "," + r + ",0,0," + (+(y01 * x20 > x01 * y20)) + "," + (this._x1 = x1 + t21 * x21) + "," + (this._y1 = y1 + t21 * y21);
    }
  },
  arc: function(x, y, r, a0, a1, ccw) {
    x = +x, y = +y, r = +r;
    var dx = r * Math.cos(a0),
        dy = r * Math.sin(a0),
        x0 = x + dx,
        y0 = y + dy,
        cw = 1 ^ ccw,
        da = ccw ? a0 - a1 : a1 - a0;

    // Is the radius negative? Error.
    if (r < 0) throw new Error("negative radius: " + r);

    // Is this path empty? Move to (x0,y0).
    if (this._x1 === null) {
      this._ += "M" + x0 + "," + y0;
    }

    // Or, is (x0,y0) not coincident with the previous point? Line to (x0,y0).
    else if (Math.abs(this._x1 - x0) > epsilon || Math.abs(this._y1 - y0) > epsilon) {
      this._ += "L" + x0 + "," + y0;
    }

    // Is this arc empty? We’re done.
    if (!r) return;

    // Does the angle go the wrong way? Flip the direction.
    if (da < 0) da = da % path_tau + path_tau;

    // Is this a complete circle? Draw two arcs to complete the circle.
    if (da > tauEpsilon) {
      this._ += "A" + r + "," + r + ",0,1," + cw + "," + (x - dx) + "," + (y - dy) + "A" + r + "," + r + ",0,1," + cw + "," + (this._x1 = x0) + "," + (this._y1 = y0);
    }

    // Is this arc non-empty? Draw an arc!
    else if (da > epsilon) {
      this._ += "A" + r + "," + r + ",0," + (+(da >= path_pi)) + "," + cw + "," + (this._x1 = x + r * Math.cos(a1)) + "," + (this._y1 = y + r * Math.sin(a1));
    }
  },
  rect: function(x, y, w, h) {
    this._ += "M" + (this._x0 = this._x1 = +x) + "," + (this._y0 = this._y1 = +y) + "h" + (+w) + "v" + (+h) + "h" + (-w) + "Z";
  },
  toString: function() {
    return this._;
  }
};

/* harmony default export */ var src_path = (path_path);

// CONCATENATED MODULE: ./node_modules/d3-path/src/index.js


// CONCATENATED MODULE: ./node_modules/d3-shape/src/constant.js
/* harmony default export */ var d3_shape_src_constant = (function(x) {
  return function constant() {
    return x;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/math.js
var abs = Math.abs;
var atan2 = Math.atan2;
var cos = Math.cos;
var math_max = Math.max;
var math_min = Math.min;
var sin = Math.sin;
var sqrt = Math.sqrt;

var math_epsilon = 1e-12;
var math_pi = Math.PI;
var math_halfPi = math_pi / 2;
var math_tau = 2 * math_pi;

function acos(x) {
  return x > 1 ? 0 : x < -1 ? math_pi : Math.acos(x);
}

function asin(x) {
  return x >= 1 ? math_halfPi : x <= -1 ? -math_halfPi : Math.asin(x);
}

// CONCATENATED MODULE: ./node_modules/d3-shape/src/arc.js




function arcInnerRadius(d) {
  return d.innerRadius;
}

function arcOuterRadius(d) {
  return d.outerRadius;
}

function arcStartAngle(d) {
  return d.startAngle;
}

function arcEndAngle(d) {
  return d.endAngle;
}

function arcPadAngle(d) {
  return d && d.padAngle; // Note: optional!
}

function intersect(x0, y0, x1, y1, x2, y2, x3, y3) {
  var x10 = x1 - x0, y10 = y1 - y0,
      x32 = x3 - x2, y32 = y3 - y2,
      t = y32 * x10 - x32 * y10;
  if (t * t < math_epsilon) return;
  t = (x32 * (y0 - y2) - y32 * (x0 - x2)) / t;
  return [x0 + t * x10, y0 + t * y10];
}

// Compute perpendicular offset line of length rc.
// http://mathworld.wolfram.com/Circle-LineIntersection.html
function cornerTangents(x0, y0, x1, y1, r1, rc, cw) {
  var x01 = x0 - x1,
      y01 = y0 - y1,
      lo = (cw ? rc : -rc) / sqrt(x01 * x01 + y01 * y01),
      ox = lo * y01,
      oy = -lo * x01,
      x11 = x0 + ox,
      y11 = y0 + oy,
      x10 = x1 + ox,
      y10 = y1 + oy,
      x00 = (x11 + x10) / 2,
      y00 = (y11 + y10) / 2,
      dx = x10 - x11,
      dy = y10 - y11,
      d2 = dx * dx + dy * dy,
      r = r1 - rc,
      D = x11 * y10 - x10 * y11,
      d = (dy < 0 ? -1 : 1) * sqrt(math_max(0, r * r * d2 - D * D)),
      cx0 = (D * dy - dx * d) / d2,
      cy0 = (-D * dx - dy * d) / d2,
      cx1 = (D * dy + dx * d) / d2,
      cy1 = (-D * dx + dy * d) / d2,
      dx0 = cx0 - x00,
      dy0 = cy0 - y00,
      dx1 = cx1 - x00,
      dy1 = cy1 - y00;

  // Pick the closer of the two intersection points.
  // TODO Is there a faster way to determine which intersection to use?
  if (dx0 * dx0 + dy0 * dy0 > dx1 * dx1 + dy1 * dy1) cx0 = cx1, cy0 = cy1;

  return {
    cx: cx0,
    cy: cy0,
    x01: -ox,
    y01: -oy,
    x11: cx0 * (r1 / r - 1),
    y11: cy0 * (r1 / r - 1)
  };
}

/* harmony default export */ var src_arc = (function() {
  var innerRadius = arcInnerRadius,
      outerRadius = arcOuterRadius,
      cornerRadius = d3_shape_src_constant(0),
      padRadius = null,
      startAngle = arcStartAngle,
      endAngle = arcEndAngle,
      padAngle = arcPadAngle,
      context = null;

  function arc() {
    var buffer,
        r,
        r0 = +innerRadius.apply(this, arguments),
        r1 = +outerRadius.apply(this, arguments),
        a0 = startAngle.apply(this, arguments) - math_halfPi,
        a1 = endAngle.apply(this, arguments) - math_halfPi,
        da = abs(a1 - a0),
        cw = a1 > a0;

    if (!context) context = buffer = src_path();

    // Ensure that the outer radius is always larger than the inner radius.
    if (r1 < r0) r = r1, r1 = r0, r0 = r;

    // Is it a point?
    if (!(r1 > math_epsilon)) context.moveTo(0, 0);

    // Or is it a circle or annulus?
    else if (da > math_tau - math_epsilon) {
      context.moveTo(r1 * cos(a0), r1 * sin(a0));
      context.arc(0, 0, r1, a0, a1, !cw);
      if (r0 > math_epsilon) {
        context.moveTo(r0 * cos(a1), r0 * sin(a1));
        context.arc(0, 0, r0, a1, a0, cw);
      }
    }

    // Or is it a circular or annular sector?
    else {
      var a01 = a0,
          a11 = a1,
          a00 = a0,
          a10 = a1,
          da0 = da,
          da1 = da,
          ap = padAngle.apply(this, arguments) / 2,
          rp = (ap > math_epsilon) && (padRadius ? +padRadius.apply(this, arguments) : sqrt(r0 * r0 + r1 * r1)),
          rc = math_min(abs(r1 - r0) / 2, +cornerRadius.apply(this, arguments)),
          rc0 = rc,
          rc1 = rc,
          t0,
          t1;

      // Apply padding? Note that since r1 ≥ r0, da1 ≥ da0.
      if (rp > math_epsilon) {
        var p0 = asin(rp / r0 * sin(ap)),
            p1 = asin(rp / r1 * sin(ap));
        if ((da0 -= p0 * 2) > math_epsilon) p0 *= (cw ? 1 : -1), a00 += p0, a10 -= p0;
        else da0 = 0, a00 = a10 = (a0 + a1) / 2;
        if ((da1 -= p1 * 2) > math_epsilon) p1 *= (cw ? 1 : -1), a01 += p1, a11 -= p1;
        else da1 = 0, a01 = a11 = (a0 + a1) / 2;
      }

      var x01 = r1 * cos(a01),
          y01 = r1 * sin(a01),
          x10 = r0 * cos(a10),
          y10 = r0 * sin(a10);

      // Apply rounded corners?
      if (rc > math_epsilon) {
        var x11 = r1 * cos(a11),
            y11 = r1 * sin(a11),
            x00 = r0 * cos(a00),
            y00 = r0 * sin(a00),
            oc;

        // Restrict the corner radius according to the sector angle.
        if (da <= math_tau - math_epsilon && (oc = intersect(x01, y01, x00, y00, x11, y11, x10, y10))) {
          var ax = x01 - oc[0],
              ay = y01 - oc[1],
              bx = x11 - oc[0],
              by = y11 - oc[1],
              kc = 1 / sin(acos((ax * bx + ay * by) / (sqrt(ax * ax + ay * ay) * sqrt(bx * bx + by * by))) / 2),
              lc = sqrt(oc[0] * oc[0] + oc[1] * oc[1]);
          rc0 = math_min(rc, (r0 - lc) / (kc - 1));
          rc1 = math_min(rc, (r1 - lc) / (kc + 1));
        }
      }

      // Is the sector collapsed to a line?
      if (!(da1 > math_epsilon)) context.moveTo(x01, y01);

      // Does the sector’s outer ring have rounded corners?
      else if (rc1 > math_epsilon) {
        t0 = cornerTangents(x00, y00, x01, y01, r1, rc1, cw);
        t1 = cornerTangents(x11, y11, x10, y10, r1, rc1, cw);

        context.moveTo(t0.cx + t0.x01, t0.cy + t0.y01);

        // Have the corners merged?
        if (rc1 < rc) context.arc(t0.cx, t0.cy, rc1, atan2(t0.y01, t0.x01), atan2(t1.y01, t1.x01), !cw);

        // Otherwise, draw the two corners and the ring.
        else {
          context.arc(t0.cx, t0.cy, rc1, atan2(t0.y01, t0.x01), atan2(t0.y11, t0.x11), !cw);
          context.arc(0, 0, r1, atan2(t0.cy + t0.y11, t0.cx + t0.x11), atan2(t1.cy + t1.y11, t1.cx + t1.x11), !cw);
          context.arc(t1.cx, t1.cy, rc1, atan2(t1.y11, t1.x11), atan2(t1.y01, t1.x01), !cw);
        }
      }

      // Or is the outer ring just a circular arc?
      else context.moveTo(x01, y01), context.arc(0, 0, r1, a01, a11, !cw);

      // Is there no inner ring, and it’s a circular sector?
      // Or perhaps it’s an annular sector collapsed due to padding?
      if (!(r0 > math_epsilon) || !(da0 > math_epsilon)) context.lineTo(x10, y10);

      // Does the sector’s inner ring (or point) have rounded corners?
      else if (rc0 > math_epsilon) {
        t0 = cornerTangents(x10, y10, x11, y11, r0, -rc0, cw);
        t1 = cornerTangents(x01, y01, x00, y00, r0, -rc0, cw);

        context.lineTo(t0.cx + t0.x01, t0.cy + t0.y01);

        // Have the corners merged?
        if (rc0 < rc) context.arc(t0.cx, t0.cy, rc0, atan2(t0.y01, t0.x01), atan2(t1.y01, t1.x01), !cw);

        // Otherwise, draw the two corners and the ring.
        else {
          context.arc(t0.cx, t0.cy, rc0, atan2(t0.y01, t0.x01), atan2(t0.y11, t0.x11), !cw);
          context.arc(0, 0, r0, atan2(t0.cy + t0.y11, t0.cx + t0.x11), atan2(t1.cy + t1.y11, t1.cx + t1.x11), cw);
          context.arc(t1.cx, t1.cy, rc0, atan2(t1.y11, t1.x11), atan2(t1.y01, t1.x01), !cw);
        }
      }

      // Or is the inner ring just a circular arc?
      else context.arc(0, 0, r0, a10, a00, cw);
    }

    context.closePath();

    if (buffer) return context = null, buffer + "" || null;
  }

  arc.centroid = function() {
    var r = (+innerRadius.apply(this, arguments) + +outerRadius.apply(this, arguments)) / 2,
        a = (+startAngle.apply(this, arguments) + +endAngle.apply(this, arguments)) / 2 - math_pi / 2;
    return [cos(a) * r, sin(a) * r];
  };

  arc.innerRadius = function(_) {
    return arguments.length ? (innerRadius = typeof _ === "function" ? _ : d3_shape_src_constant(+_), arc) : innerRadius;
  };

  arc.outerRadius = function(_) {
    return arguments.length ? (outerRadius = typeof _ === "function" ? _ : d3_shape_src_constant(+_), arc) : outerRadius;
  };

  arc.cornerRadius = function(_) {
    return arguments.length ? (cornerRadius = typeof _ === "function" ? _ : d3_shape_src_constant(+_), arc) : cornerRadius;
  };

  arc.padRadius = function(_) {
    return arguments.length ? (padRadius = _ == null ? null : typeof _ === "function" ? _ : d3_shape_src_constant(+_), arc) : padRadius;
  };

  arc.startAngle = function(_) {
    return arguments.length ? (startAngle = typeof _ === "function" ? _ : d3_shape_src_constant(+_), arc) : startAngle;
  };

  arc.endAngle = function(_) {
    return arguments.length ? (endAngle = typeof _ === "function" ? _ : d3_shape_src_constant(+_), arc) : endAngle;
  };

  arc.padAngle = function(_) {
    return arguments.length ? (padAngle = typeof _ === "function" ? _ : d3_shape_src_constant(+_), arc) : padAngle;
  };

  arc.context = function(_) {
    return arguments.length ? ((context = _ == null ? null : _), arc) : context;
  };

  return arc;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/linear.js
function Linear(context) {
  this._context = context;
}

Linear.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._point = 0;
  },
  lineEnd: function() {
    if (this._line || (this._line !== 0 && this._point === 1)) this._context.closePath();
    this._line = 1 - this._line;
  },
  point: function(x, y) {
    x = +x, y = +y;
    switch (this._point) {
      case 0: this._point = 1; this._line ? this._context.lineTo(x, y) : this._context.moveTo(x, y); break;
      case 1: this._point = 2; // proceed
      default: this._context.lineTo(x, y); break;
    }
  }
};

/* harmony default export */ var curve_linear = (function(context) {
  return new Linear(context);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/point.js
function point_x(p) {
  return p[0];
}

function point_y(p) {
  return p[1];
}

// CONCATENATED MODULE: ./node_modules/d3-shape/src/line.js





/* harmony default export */ var src_line = (function() {
  var x = point_x,
      y = point_y,
      defined = d3_shape_src_constant(true),
      context = null,
      curve = curve_linear,
      output = null;

  function line(data) {
    var i,
        n = data.length,
        d,
        defined0 = false,
        buffer;

    if (context == null) output = curve(buffer = src_path());

    for (i = 0; i <= n; ++i) {
      if (!(i < n && defined(d = data[i], i, data)) === defined0) {
        if (defined0 = !defined0) output.lineStart();
        else output.lineEnd();
      }
      if (defined0) output.point(+x(d, i, data), +y(d, i, data));
    }

    if (buffer) return output = null, buffer + "" || null;
  }

  line.x = function(_) {
    return arguments.length ? (x = typeof _ === "function" ? _ : d3_shape_src_constant(+_), line) : x;
  };

  line.y = function(_) {
    return arguments.length ? (y = typeof _ === "function" ? _ : d3_shape_src_constant(+_), line) : y;
  };

  line.defined = function(_) {
    return arguments.length ? (defined = typeof _ === "function" ? _ : d3_shape_src_constant(!!_), line) : defined;
  };

  line.curve = function(_) {
    return arguments.length ? (curve = _, context != null && (output = curve(context)), line) : curve;
  };

  line.context = function(_) {
    return arguments.length ? (_ == null ? context = output = null : output = curve(context = _), line) : context;
  };

  return line;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/area.js






/* harmony default export */ var src_area = (function() {
  var x0 = point_x,
      x1 = null,
      y0 = d3_shape_src_constant(0),
      y1 = point_y,
      defined = d3_shape_src_constant(true),
      context = null,
      curve = curve_linear,
      output = null;

  function area(data) {
    var i,
        j,
        k,
        n = data.length,
        d,
        defined0 = false,
        buffer,
        x0z = new Array(n),
        y0z = new Array(n);

    if (context == null) output = curve(buffer = src_path());

    for (i = 0; i <= n; ++i) {
      if (!(i < n && defined(d = data[i], i, data)) === defined0) {
        if (defined0 = !defined0) {
          j = i;
          output.areaStart();
          output.lineStart();
        } else {
          output.lineEnd();
          output.lineStart();
          for (k = i - 1; k >= j; --k) {
            output.point(x0z[k], y0z[k]);
          }
          output.lineEnd();
          output.areaEnd();
        }
      }
      if (defined0) {
        x0z[i] = +x0(d, i, data), y0z[i] = +y0(d, i, data);
        output.point(x1 ? +x1(d, i, data) : x0z[i], y1 ? +y1(d, i, data) : y0z[i]);
      }
    }

    if (buffer) return output = null, buffer + "" || null;
  }

  function arealine() {
    return src_line().defined(defined).curve(curve).context(context);
  }

  area.x = function(_) {
    return arguments.length ? (x0 = typeof _ === "function" ? _ : d3_shape_src_constant(+_), x1 = null, area) : x0;
  };

  area.x0 = function(_) {
    return arguments.length ? (x0 = typeof _ === "function" ? _ : d3_shape_src_constant(+_), area) : x0;
  };

  area.x1 = function(_) {
    return arguments.length ? (x1 = _ == null ? null : typeof _ === "function" ? _ : d3_shape_src_constant(+_), area) : x1;
  };

  area.y = function(_) {
    return arguments.length ? (y0 = typeof _ === "function" ? _ : d3_shape_src_constant(+_), y1 = null, area) : y0;
  };

  area.y0 = function(_) {
    return arguments.length ? (y0 = typeof _ === "function" ? _ : d3_shape_src_constant(+_), area) : y0;
  };

  area.y1 = function(_) {
    return arguments.length ? (y1 = _ == null ? null : typeof _ === "function" ? _ : d3_shape_src_constant(+_), area) : y1;
  };

  area.lineX0 =
  area.lineY0 = function() {
    return arealine().x(x0).y(y0);
  };

  area.lineY1 = function() {
    return arealine().x(x0).y(y1);
  };

  area.lineX1 = function() {
    return arealine().x(x1).y(y0);
  };

  area.defined = function(_) {
    return arguments.length ? (defined = typeof _ === "function" ? _ : d3_shape_src_constant(!!_), area) : defined;
  };

  area.curve = function(_) {
    return arguments.length ? (curve = _, context != null && (output = curve(context)), area) : curve;
  };

  area.context = function(_) {
    return arguments.length ? (_ == null ? context = output = null : output = curve(context = _), area) : context;
  };

  return area;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/descending.js
/* harmony default export */ var descending = (function(a, b) {
  return b < a ? -1 : b > a ? 1 : b >= a ? 0 : NaN;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/identity.js
/* harmony default export */ var src_identity = (function(d) {
  return d;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/pie.js





/* harmony default export */ var src_pie = (function() {
  var value = src_identity,
      sortValues = descending,
      sort = null,
      startAngle = d3_shape_src_constant(0),
      endAngle = d3_shape_src_constant(math_tau),
      padAngle = d3_shape_src_constant(0);

  function pie(data) {
    var i,
        n = data.length,
        j,
        k,
        sum = 0,
        index = new Array(n),
        arcs = new Array(n),
        a0 = +startAngle.apply(this, arguments),
        da = Math.min(math_tau, Math.max(-math_tau, endAngle.apply(this, arguments) - a0)),
        a1,
        p = Math.min(Math.abs(da) / n, padAngle.apply(this, arguments)),
        pa = p * (da < 0 ? -1 : 1),
        v;

    for (i = 0; i < n; ++i) {
      if ((v = arcs[index[i] = i] = +value(data[i], i, data)) > 0) {
        sum += v;
      }
    }

    // Optionally sort the arcs by previously-computed values or by data.
    if (sortValues != null) index.sort(function(i, j) { return sortValues(arcs[i], arcs[j]); });
    else if (sort != null) index.sort(function(i, j) { return sort(data[i], data[j]); });

    // Compute the arcs! They are stored in the original data's order.
    for (i = 0, k = sum ? (da - n * pa) / sum : 0; i < n; ++i, a0 = a1) {
      j = index[i], v = arcs[j], a1 = a0 + (v > 0 ? v * k : 0) + pa, arcs[j] = {
        data: data[j],
        index: i,
        value: v,
        startAngle: a0,
        endAngle: a1,
        padAngle: p
      };
    }

    return arcs;
  }

  pie.value = function(_) {
    return arguments.length ? (value = typeof _ === "function" ? _ : d3_shape_src_constant(+_), pie) : value;
  };

  pie.sortValues = function(_) {
    return arguments.length ? (sortValues = _, sort = null, pie) : sortValues;
  };

  pie.sort = function(_) {
    return arguments.length ? (sort = _, sortValues = null, pie) : sort;
  };

  pie.startAngle = function(_) {
    return arguments.length ? (startAngle = typeof _ === "function" ? _ : d3_shape_src_constant(+_), pie) : startAngle;
  };

  pie.endAngle = function(_) {
    return arguments.length ? (endAngle = typeof _ === "function" ? _ : d3_shape_src_constant(+_), pie) : endAngle;
  };

  pie.padAngle = function(_) {
    return arguments.length ? (padAngle = typeof _ === "function" ? _ : d3_shape_src_constant(+_), pie) : padAngle;
  };

  return pie;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/radial.js


var curveRadialLinear = curveRadial(curve_linear);

function Radial(curve) {
  this._curve = curve;
}

Radial.prototype = {
  areaStart: function() {
    this._curve.areaStart();
  },
  areaEnd: function() {
    this._curve.areaEnd();
  },
  lineStart: function() {
    this._curve.lineStart();
  },
  lineEnd: function() {
    this._curve.lineEnd();
  },
  point: function(a, r) {
    this._curve.point(r * Math.sin(a), r * -Math.cos(a));
  }
};

function curveRadial(curve) {

  function radial(context) {
    return new Radial(curve(context));
  }

  radial._curve = curve;

  return radial;
}

// CONCATENATED MODULE: ./node_modules/d3-shape/src/lineRadial.js



function lineRadial(l) {
  var c = l.curve;

  l.angle = l.x, delete l.x;
  l.radius = l.y, delete l.y;

  l.curve = function(_) {
    return arguments.length ? c(curveRadial(_)) : c()._curve;
  };

  return l;
}

/* harmony default export */ var src_lineRadial = (function() {
  return lineRadial(src_line().curve(curveRadialLinear));
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/areaRadial.js




/* harmony default export */ var areaRadial = (function() {
  var a = src_area().curve(curveRadialLinear),
      c = a.curve,
      x0 = a.lineX0,
      x1 = a.lineX1,
      y0 = a.lineY0,
      y1 = a.lineY1;

  a.angle = a.x, delete a.x;
  a.startAngle = a.x0, delete a.x0;
  a.endAngle = a.x1, delete a.x1;
  a.radius = a.y, delete a.y;
  a.innerRadius = a.y0, delete a.y0;
  a.outerRadius = a.y1, delete a.y1;
  a.lineStartAngle = function() { return lineRadial(x0()); }, delete a.lineX0;
  a.lineEndAngle = function() { return lineRadial(x1()); }, delete a.lineX1;
  a.lineInnerRadius = function() { return lineRadial(y0()); }, delete a.lineY0;
  a.lineOuterRadius = function() { return lineRadial(y1()); }, delete a.lineY1;

  a.curve = function(_) {
    return arguments.length ? c(curveRadial(_)) : c()._curve;
  };

  return a;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/pointRadial.js
/* harmony default export */ var pointRadial = (function(x, y) {
  return [(y = +y) * Math.cos(x -= Math.PI / 2), y * Math.sin(x)];
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/array.js
var array_slice = Array.prototype.slice;

// CONCATENATED MODULE: ./node_modules/d3-shape/src/link/index.js






function linkSource(d) {
  return d.source;
}

function linkTarget(d) {
  return d.target;
}

function link_link(curve) {
  var source = linkSource,
      target = linkTarget,
      x = point_x,
      y = point_y,
      context = null;

  function link() {
    var buffer, argv = array_slice.call(arguments), s = source.apply(this, argv), t = target.apply(this, argv);
    if (!context) context = buffer = src_path();
    curve(context, +x.apply(this, (argv[0] = s, argv)), +y.apply(this, argv), +x.apply(this, (argv[0] = t, argv)), +y.apply(this, argv));
    if (buffer) return context = null, buffer + "" || null;
  }

  link.source = function(_) {
    return arguments.length ? (source = _, link) : source;
  };

  link.target = function(_) {
    return arguments.length ? (target = _, link) : target;
  };

  link.x = function(_) {
    return arguments.length ? (x = typeof _ === "function" ? _ : d3_shape_src_constant(+_), link) : x;
  };

  link.y = function(_) {
    return arguments.length ? (y = typeof _ === "function" ? _ : d3_shape_src_constant(+_), link) : y;
  };

  link.context = function(_) {
    return arguments.length ? ((context = _ == null ? null : _), link) : context;
  };

  return link;
}

function curveHorizontal(context, x0, y0, x1, y1) {
  context.moveTo(x0, y0);
  context.bezierCurveTo(x0 = (x0 + x1) / 2, y0, x0, y1, x1, y1);
}

function curveVertical(context, x0, y0, x1, y1) {
  context.moveTo(x0, y0);
  context.bezierCurveTo(x0, y0 = (y0 + y1) / 2, x1, y0, x1, y1);
}

function link_curveRadial(context, x0, y0, x1, y1) {
  var p0 = pointRadial(x0, y0),
      p1 = pointRadial(x0, y0 = (y0 + y1) / 2),
      p2 = pointRadial(x1, y0),
      p3 = pointRadial(x1, y1);
  context.moveTo(p0[0], p0[1]);
  context.bezierCurveTo(p1[0], p1[1], p2[0], p2[1], p3[0], p3[1]);
}

function linkHorizontal() {
  return link_link(curveHorizontal);
}

function linkVertical() {
  return link_link(curveVertical);
}

function linkRadial() {
  var l = link_link(link_curveRadial);
  l.angle = l.x, delete l.x;
  l.radius = l.y, delete l.y;
  return l;
}

// CONCATENATED MODULE: ./node_modules/d3-shape/src/symbol/circle.js


/* harmony default export */ var circle = ({
  draw: function(context, size) {
    var r = Math.sqrt(size / math_pi);
    context.moveTo(r, 0);
    context.arc(0, 0, r, 0, math_tau);
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/symbol/cross.js
/* harmony default export */ var cross = ({
  draw: function(context, size) {
    var r = Math.sqrt(size / 5) / 2;
    context.moveTo(-3 * r, -r);
    context.lineTo(-r, -r);
    context.lineTo(-r, -3 * r);
    context.lineTo(r, -3 * r);
    context.lineTo(r, -r);
    context.lineTo(3 * r, -r);
    context.lineTo(3 * r, r);
    context.lineTo(r, r);
    context.lineTo(r, 3 * r);
    context.lineTo(-r, 3 * r);
    context.lineTo(-r, r);
    context.lineTo(-3 * r, r);
    context.closePath();
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/symbol/diamond.js
var tan30 = Math.sqrt(1 / 3),
    tan30_2 = tan30 * 2;

/* harmony default export */ var diamond = ({
  draw: function(context, size) {
    var y = Math.sqrt(size / tan30_2),
        x = y * tan30;
    context.moveTo(0, -y);
    context.lineTo(x, 0);
    context.lineTo(0, y);
    context.lineTo(-x, 0);
    context.closePath();
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/symbol/star.js


var ka = 0.89081309152928522810,
    kr = Math.sin(math_pi / 10) / Math.sin(7 * math_pi / 10),
    kx = Math.sin(math_tau / 10) * kr,
    ky = -Math.cos(math_tau / 10) * kr;

/* harmony default export */ var star = ({
  draw: function(context, size) {
    var r = Math.sqrt(size * ka),
        x = kx * r,
        y = ky * r;
    context.moveTo(0, -r);
    context.lineTo(x, y);
    for (var i = 1; i < 5; ++i) {
      var a = math_tau * i / 5,
          c = Math.cos(a),
          s = Math.sin(a);
      context.lineTo(s * r, -c * r);
      context.lineTo(c * x - s * y, s * x + c * y);
    }
    context.closePath();
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/symbol/square.js
/* harmony default export */ var square = ({
  draw: function(context, size) {
    var w = Math.sqrt(size),
        x = -w / 2;
    context.rect(x, x, w, w);
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/symbol/triangle.js
var sqrt3 = Math.sqrt(3);

/* harmony default export */ var triangle = ({
  draw: function(context, size) {
    var y = -Math.sqrt(size / (sqrt3 * 3));
    context.moveTo(0, y * 2);
    context.lineTo(-sqrt3 * y, -y);
    context.lineTo(sqrt3 * y, -y);
    context.closePath();
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/symbol/wye.js
var wye_c = -0.5,
    wye_s = Math.sqrt(3) / 2,
    wye_k = 1 / Math.sqrt(12),
    wye_a = (wye_k / 2 + 1) * 3;

/* harmony default export */ var wye = ({
  draw: function(context, size) {
    var r = Math.sqrt(size / wye_a),
        x0 = r / 2,
        y0 = r * wye_k,
        x1 = x0,
        y1 = r * wye_k + r,
        x2 = -x1,
        y2 = y1;
    context.moveTo(x0, y0);
    context.lineTo(x1, y1);
    context.lineTo(x2, y2);
    context.lineTo(wye_c * x0 - wye_s * y0, wye_s * x0 + wye_c * y0);
    context.lineTo(wye_c * x1 - wye_s * y1, wye_s * x1 + wye_c * y1);
    context.lineTo(wye_c * x2 - wye_s * y2, wye_s * x2 + wye_c * y2);
    context.lineTo(wye_c * x0 + wye_s * y0, wye_c * y0 - wye_s * x0);
    context.lineTo(wye_c * x1 + wye_s * y1, wye_c * y1 - wye_s * x1);
    context.lineTo(wye_c * x2 + wye_s * y2, wye_c * y2 - wye_s * x2);
    context.closePath();
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/symbol.js










var symbols = [
  circle,
  cross,
  diamond,
  square,
  star,
  triangle,
  wye
];

/* harmony default export */ var src_symbol = (function() {
  var type = d3_shape_src_constant(circle),
      size = d3_shape_src_constant(64),
      context = null;

  function symbol() {
    var buffer;
    if (!context) context = buffer = src_path();
    type.apply(this, arguments).draw(context, +size.apply(this, arguments));
    if (buffer) return context = null, buffer + "" || null;
  }

  symbol.type = function(_) {
    return arguments.length ? (type = typeof _ === "function" ? _ : d3_shape_src_constant(_), symbol) : type;
  };

  symbol.size = function(_) {
    return arguments.length ? (size = typeof _ === "function" ? _ : d3_shape_src_constant(+_), symbol) : size;
  };

  symbol.context = function(_) {
    return arguments.length ? (context = _ == null ? null : _, symbol) : context;
  };

  return symbol;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/noop.js
/* harmony default export */ var src_noop = (function() {});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/basis.js
function basis_point(that, x, y) {
  that._context.bezierCurveTo(
    (2 * that._x0 + that._x1) / 3,
    (2 * that._y0 + that._y1) / 3,
    (that._x0 + 2 * that._x1) / 3,
    (that._y0 + 2 * that._y1) / 3,
    (that._x0 + 4 * that._x1 + x) / 6,
    (that._y0 + 4 * that._y1 + y) / 6
  );
}

function Basis(context) {
  this._context = context;
}

Basis.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x0 = this._x1 =
    this._y0 = this._y1 = NaN;
    this._point = 0;
  },
  lineEnd: function() {
    switch (this._point) {
      case 3: basis_point(this, this._x1, this._y1); // proceed
      case 2: this._context.lineTo(this._x1, this._y1); break;
    }
    if (this._line || (this._line !== 0 && this._point === 1)) this._context.closePath();
    this._line = 1 - this._line;
  },
  point: function(x, y) {
    x = +x, y = +y;
    switch (this._point) {
      case 0: this._point = 1; this._line ? this._context.lineTo(x, y) : this._context.moveTo(x, y); break;
      case 1: this._point = 2; break;
      case 2: this._point = 3; this._context.lineTo((5 * this._x0 + this._x1) / 6, (5 * this._y0 + this._y1) / 6); // proceed
      default: basis_point(this, x, y); break;
    }
    this._x0 = this._x1, this._x1 = x;
    this._y0 = this._y1, this._y1 = y;
  }
};

/* harmony default export */ var curve_basis = (function(context) {
  return new Basis(context);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/basisClosed.js



function BasisClosed(context) {
  this._context = context;
}

BasisClosed.prototype = {
  areaStart: src_noop,
  areaEnd: src_noop,
  lineStart: function() {
    this._x0 = this._x1 = this._x2 = this._x3 = this._x4 =
    this._y0 = this._y1 = this._y2 = this._y3 = this._y4 = NaN;
    this._point = 0;
  },
  lineEnd: function() {
    switch (this._point) {
      case 1: {
        this._context.moveTo(this._x2, this._y2);
        this._context.closePath();
        break;
      }
      case 2: {
        this._context.moveTo((this._x2 + 2 * this._x3) / 3, (this._y2 + 2 * this._y3) / 3);
        this._context.lineTo((this._x3 + 2 * this._x2) / 3, (this._y3 + 2 * this._y2) / 3);
        this._context.closePath();
        break;
      }
      case 3: {
        this.point(this._x2, this._y2);
        this.point(this._x3, this._y3);
        this.point(this._x4, this._y4);
        break;
      }
    }
  },
  point: function(x, y) {
    x = +x, y = +y;
    switch (this._point) {
      case 0: this._point = 1; this._x2 = x, this._y2 = y; break;
      case 1: this._point = 2; this._x3 = x, this._y3 = y; break;
      case 2: this._point = 3; this._x4 = x, this._y4 = y; this._context.moveTo((this._x0 + 4 * this._x1 + x) / 6, (this._y0 + 4 * this._y1 + y) / 6); break;
      default: basis_point(this, x, y); break;
    }
    this._x0 = this._x1, this._x1 = x;
    this._y0 = this._y1, this._y1 = y;
  }
};

/* harmony default export */ var curve_basisClosed = (function(context) {
  return new BasisClosed(context);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/basisOpen.js


function BasisOpen(context) {
  this._context = context;
}

BasisOpen.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x0 = this._x1 =
    this._y0 = this._y1 = NaN;
    this._point = 0;
  },
  lineEnd: function() {
    if (this._line || (this._line !== 0 && this._point === 3)) this._context.closePath();
    this._line = 1 - this._line;
  },
  point: function(x, y) {
    x = +x, y = +y;
    switch (this._point) {
      case 0: this._point = 1; break;
      case 1: this._point = 2; break;
      case 2: this._point = 3; var x0 = (this._x0 + 4 * this._x1 + x) / 6, y0 = (this._y0 + 4 * this._y1 + y) / 6; this._line ? this._context.lineTo(x0, y0) : this._context.moveTo(x0, y0); break;
      case 3: this._point = 4; // proceed
      default: basis_point(this, x, y); break;
    }
    this._x0 = this._x1, this._x1 = x;
    this._y0 = this._y1, this._y1 = y;
  }
};

/* harmony default export */ var basisOpen = (function(context) {
  return new BasisOpen(context);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/bundle.js


function Bundle(context, beta) {
  this._basis = new Basis(context);
  this._beta = beta;
}

Bundle.prototype = {
  lineStart: function() {
    this._x = [];
    this._y = [];
    this._basis.lineStart();
  },
  lineEnd: function() {
    var x = this._x,
        y = this._y,
        j = x.length - 1;

    if (j > 0) {
      var x0 = x[0],
          y0 = y[0],
          dx = x[j] - x0,
          dy = y[j] - y0,
          i = -1,
          t;

      while (++i <= j) {
        t = i / j;
        this._basis.point(
          this._beta * x[i] + (1 - this._beta) * (x0 + t * dx),
          this._beta * y[i] + (1 - this._beta) * (y0 + t * dy)
        );
      }
    }

    this._x = this._y = null;
    this._basis.lineEnd();
  },
  point: function(x, y) {
    this._x.push(+x);
    this._y.push(+y);
  }
};

/* harmony default export */ var curve_bundle = ((function custom(beta) {

  function bundle(context) {
    return beta === 1 ? new Basis(context) : new Bundle(context, beta);
  }

  bundle.beta = function(beta) {
    return custom(+beta);
  };

  return bundle;
})(0.85));

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/cardinal.js
function cardinal_point(that, x, y) {
  that._context.bezierCurveTo(
    that._x1 + that._k * (that._x2 - that._x0),
    that._y1 + that._k * (that._y2 - that._y0),
    that._x2 + that._k * (that._x1 - x),
    that._y2 + that._k * (that._y1 - y),
    that._x2,
    that._y2
  );
}

function Cardinal(context, tension) {
  this._context = context;
  this._k = (1 - tension) / 6;
}

Cardinal.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x0 = this._x1 = this._x2 =
    this._y0 = this._y1 = this._y2 = NaN;
    this._point = 0;
  },
  lineEnd: function() {
    switch (this._point) {
      case 2: this._context.lineTo(this._x2, this._y2); break;
      case 3: cardinal_point(this, this._x1, this._y1); break;
    }
    if (this._line || (this._line !== 0 && this._point === 1)) this._context.closePath();
    this._line = 1 - this._line;
  },
  point: function(x, y) {
    x = +x, y = +y;
    switch (this._point) {
      case 0: this._point = 1; this._line ? this._context.lineTo(x, y) : this._context.moveTo(x, y); break;
      case 1: this._point = 2; this._x1 = x, this._y1 = y; break;
      case 2: this._point = 3; // proceed
      default: cardinal_point(this, x, y); break;
    }
    this._x0 = this._x1, this._x1 = this._x2, this._x2 = x;
    this._y0 = this._y1, this._y1 = this._y2, this._y2 = y;
  }
};

/* harmony default export */ var cardinal = ((function custom(tension) {

  function cardinal(context) {
    return new Cardinal(context, tension);
  }

  cardinal.tension = function(tension) {
    return custom(+tension);
  };

  return cardinal;
})(0));

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/cardinalClosed.js



function CardinalClosed(context, tension) {
  this._context = context;
  this._k = (1 - tension) / 6;
}

CardinalClosed.prototype = {
  areaStart: src_noop,
  areaEnd: src_noop,
  lineStart: function() {
    this._x0 = this._x1 = this._x2 = this._x3 = this._x4 = this._x5 =
    this._y0 = this._y1 = this._y2 = this._y3 = this._y4 = this._y5 = NaN;
    this._point = 0;
  },
  lineEnd: function() {
    switch (this._point) {
      case 1: {
        this._context.moveTo(this._x3, this._y3);
        this._context.closePath();
        break;
      }
      case 2: {
        this._context.lineTo(this._x3, this._y3);
        this._context.closePath();
        break;
      }
      case 3: {
        this.point(this._x3, this._y3);
        this.point(this._x4, this._y4);
        this.point(this._x5, this._y5);
        break;
      }
    }
  },
  point: function(x, y) {
    x = +x, y = +y;
    switch (this._point) {
      case 0: this._point = 1; this._x3 = x, this._y3 = y; break;
      case 1: this._point = 2; this._context.moveTo(this._x4 = x, this._y4 = y); break;
      case 2: this._point = 3; this._x5 = x, this._y5 = y; break;
      default: cardinal_point(this, x, y); break;
    }
    this._x0 = this._x1, this._x1 = this._x2, this._x2 = x;
    this._y0 = this._y1, this._y1 = this._y2, this._y2 = y;
  }
};

/* harmony default export */ var cardinalClosed = ((function custom(tension) {

  function cardinal(context) {
    return new CardinalClosed(context, tension);
  }

  cardinal.tension = function(tension) {
    return custom(+tension);
  };

  return cardinal;
})(0));

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/cardinalOpen.js


function CardinalOpen(context, tension) {
  this._context = context;
  this._k = (1 - tension) / 6;
}

CardinalOpen.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x0 = this._x1 = this._x2 =
    this._y0 = this._y1 = this._y2 = NaN;
    this._point = 0;
  },
  lineEnd: function() {
    if (this._line || (this._line !== 0 && this._point === 3)) this._context.closePath();
    this._line = 1 - this._line;
  },
  point: function(x, y) {
    x = +x, y = +y;
    switch (this._point) {
      case 0: this._point = 1; break;
      case 1: this._point = 2; break;
      case 2: this._point = 3; this._line ? this._context.lineTo(this._x2, this._y2) : this._context.moveTo(this._x2, this._y2); break;
      case 3: this._point = 4; // proceed
      default: cardinal_point(this, x, y); break;
    }
    this._x0 = this._x1, this._x1 = this._x2, this._x2 = x;
    this._y0 = this._y1, this._y1 = this._y2, this._y2 = y;
  }
};

/* harmony default export */ var cardinalOpen = ((function custom(tension) {

  function cardinal(context) {
    return new CardinalOpen(context, tension);
  }

  cardinal.tension = function(tension) {
    return custom(+tension);
  };

  return cardinal;
})(0));

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/catmullRom.js



function catmullRom_point(that, x, y) {
  var x1 = that._x1,
      y1 = that._y1,
      x2 = that._x2,
      y2 = that._y2;

  if (that._l01_a > math_epsilon) {
    var a = 2 * that._l01_2a + 3 * that._l01_a * that._l12_a + that._l12_2a,
        n = 3 * that._l01_a * (that._l01_a + that._l12_a);
    x1 = (x1 * a - that._x0 * that._l12_2a + that._x2 * that._l01_2a) / n;
    y1 = (y1 * a - that._y0 * that._l12_2a + that._y2 * that._l01_2a) / n;
  }

  if (that._l23_a > math_epsilon) {
    var b = 2 * that._l23_2a + 3 * that._l23_a * that._l12_a + that._l12_2a,
        m = 3 * that._l23_a * (that._l23_a + that._l12_a);
    x2 = (x2 * b + that._x1 * that._l23_2a - x * that._l12_2a) / m;
    y2 = (y2 * b + that._y1 * that._l23_2a - y * that._l12_2a) / m;
  }

  that._context.bezierCurveTo(x1, y1, x2, y2, that._x2, that._y2);
}

function CatmullRom(context, alpha) {
  this._context = context;
  this._alpha = alpha;
}

CatmullRom.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x0 = this._x1 = this._x2 =
    this._y0 = this._y1 = this._y2 = NaN;
    this._l01_a = this._l12_a = this._l23_a =
    this._l01_2a = this._l12_2a = this._l23_2a =
    this._point = 0;
  },
  lineEnd: function() {
    switch (this._point) {
      case 2: this._context.lineTo(this._x2, this._y2); break;
      case 3: this.point(this._x2, this._y2); break;
    }
    if (this._line || (this._line !== 0 && this._point === 1)) this._context.closePath();
    this._line = 1 - this._line;
  },
  point: function(x, y) {
    x = +x, y = +y;

    if (this._point) {
      var x23 = this._x2 - x,
          y23 = this._y2 - y;
      this._l23_a = Math.sqrt(this._l23_2a = Math.pow(x23 * x23 + y23 * y23, this._alpha));
    }

    switch (this._point) {
      case 0: this._point = 1; this._line ? this._context.lineTo(x, y) : this._context.moveTo(x, y); break;
      case 1: this._point = 2; break;
      case 2: this._point = 3; // proceed
      default: catmullRom_point(this, x, y); break;
    }

    this._l01_a = this._l12_a, this._l12_a = this._l23_a;
    this._l01_2a = this._l12_2a, this._l12_2a = this._l23_2a;
    this._x0 = this._x1, this._x1 = this._x2, this._x2 = x;
    this._y0 = this._y1, this._y1 = this._y2, this._y2 = y;
  }
};

/* harmony default export */ var curve_catmullRom = ((function custom(alpha) {

  function catmullRom(context) {
    return alpha ? new CatmullRom(context, alpha) : new Cardinal(context, 0);
  }

  catmullRom.alpha = function(alpha) {
    return custom(+alpha);
  };

  return catmullRom;
})(0.5));

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/catmullRomClosed.js




function CatmullRomClosed(context, alpha) {
  this._context = context;
  this._alpha = alpha;
}

CatmullRomClosed.prototype = {
  areaStart: src_noop,
  areaEnd: src_noop,
  lineStart: function() {
    this._x0 = this._x1 = this._x2 = this._x3 = this._x4 = this._x5 =
    this._y0 = this._y1 = this._y2 = this._y3 = this._y4 = this._y5 = NaN;
    this._l01_a = this._l12_a = this._l23_a =
    this._l01_2a = this._l12_2a = this._l23_2a =
    this._point = 0;
  },
  lineEnd: function() {
    switch (this._point) {
      case 1: {
        this._context.moveTo(this._x3, this._y3);
        this._context.closePath();
        break;
      }
      case 2: {
        this._context.lineTo(this._x3, this._y3);
        this._context.closePath();
        break;
      }
      case 3: {
        this.point(this._x3, this._y3);
        this.point(this._x4, this._y4);
        this.point(this._x5, this._y5);
        break;
      }
    }
  },
  point: function(x, y) {
    x = +x, y = +y;

    if (this._point) {
      var x23 = this._x2 - x,
          y23 = this._y2 - y;
      this._l23_a = Math.sqrt(this._l23_2a = Math.pow(x23 * x23 + y23 * y23, this._alpha));
    }

    switch (this._point) {
      case 0: this._point = 1; this._x3 = x, this._y3 = y; break;
      case 1: this._point = 2; this._context.moveTo(this._x4 = x, this._y4 = y); break;
      case 2: this._point = 3; this._x5 = x, this._y5 = y; break;
      default: catmullRom_point(this, x, y); break;
    }

    this._l01_a = this._l12_a, this._l12_a = this._l23_a;
    this._l01_2a = this._l12_2a, this._l12_2a = this._l23_2a;
    this._x0 = this._x1, this._x1 = this._x2, this._x2 = x;
    this._y0 = this._y1, this._y1 = this._y2, this._y2 = y;
  }
};

/* harmony default export */ var catmullRomClosed = ((function custom(alpha) {

  function catmullRom(context) {
    return alpha ? new CatmullRomClosed(context, alpha) : new CardinalClosed(context, 0);
  }

  catmullRom.alpha = function(alpha) {
    return custom(+alpha);
  };

  return catmullRom;
})(0.5));

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/catmullRomOpen.js



function CatmullRomOpen(context, alpha) {
  this._context = context;
  this._alpha = alpha;
}

CatmullRomOpen.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x0 = this._x1 = this._x2 =
    this._y0 = this._y1 = this._y2 = NaN;
    this._l01_a = this._l12_a = this._l23_a =
    this._l01_2a = this._l12_2a = this._l23_2a =
    this._point = 0;
  },
  lineEnd: function() {
    if (this._line || (this._line !== 0 && this._point === 3)) this._context.closePath();
    this._line = 1 - this._line;
  },
  point: function(x, y) {
    x = +x, y = +y;

    if (this._point) {
      var x23 = this._x2 - x,
          y23 = this._y2 - y;
      this._l23_a = Math.sqrt(this._l23_2a = Math.pow(x23 * x23 + y23 * y23, this._alpha));
    }

    switch (this._point) {
      case 0: this._point = 1; break;
      case 1: this._point = 2; break;
      case 2: this._point = 3; this._line ? this._context.lineTo(this._x2, this._y2) : this._context.moveTo(this._x2, this._y2); break;
      case 3: this._point = 4; // proceed
      default: catmullRom_point(this, x, y); break;
    }

    this._l01_a = this._l12_a, this._l12_a = this._l23_a;
    this._l01_2a = this._l12_2a, this._l12_2a = this._l23_2a;
    this._x0 = this._x1, this._x1 = this._x2, this._x2 = x;
    this._y0 = this._y1, this._y1 = this._y2, this._y2 = y;
  }
};

/* harmony default export */ var catmullRomOpen = ((function custom(alpha) {

  function catmullRom(context) {
    return alpha ? new CatmullRomOpen(context, alpha) : new CardinalOpen(context, 0);
  }

  catmullRom.alpha = function(alpha) {
    return custom(+alpha);
  };

  return catmullRom;
})(0.5));

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/linearClosed.js


function LinearClosed(context) {
  this._context = context;
}

LinearClosed.prototype = {
  areaStart: src_noop,
  areaEnd: src_noop,
  lineStart: function() {
    this._point = 0;
  },
  lineEnd: function() {
    if (this._point) this._context.closePath();
  },
  point: function(x, y) {
    x = +x, y = +y;
    if (this._point) this._context.lineTo(x, y);
    else this._point = 1, this._context.moveTo(x, y);
  }
};

/* harmony default export */ var linearClosed = (function(context) {
  return new LinearClosed(context);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/monotone.js
function sign(x) {
  return x < 0 ? -1 : 1;
}

// Calculate the slopes of the tangents (Hermite-type interpolation) based on
// the following paper: Steffen, M. 1990. A Simple Method for Monotonic
// Interpolation in One Dimension. Astronomy and Astrophysics, Vol. 239, NO.
// NOV(II), P. 443, 1990.
function slope3(that, x2, y2) {
  var h0 = that._x1 - that._x0,
      h1 = x2 - that._x1,
      s0 = (that._y1 - that._y0) / (h0 || h1 < 0 && -0),
      s1 = (y2 - that._y1) / (h1 || h0 < 0 && -0),
      p = (s0 * h1 + s1 * h0) / (h0 + h1);
  return (sign(s0) + sign(s1)) * Math.min(Math.abs(s0), Math.abs(s1), 0.5 * Math.abs(p)) || 0;
}

// Calculate a one-sided slope.
function slope2(that, t) {
  var h = that._x1 - that._x0;
  return h ? (3 * (that._y1 - that._y0) / h - t) / 2 : t;
}

// According to https://en.wikipedia.org/wiki/Cubic_Hermite_spline#Representations
// "you can express cubic Hermite interpolation in terms of cubic Bézier curves
// with respect to the four values p0, p0 + m0 / 3, p1 - m1 / 3, p1".
function monotone_point(that, t0, t1) {
  var x0 = that._x0,
      y0 = that._y0,
      x1 = that._x1,
      y1 = that._y1,
      dx = (x1 - x0) / 3;
  that._context.bezierCurveTo(x0 + dx, y0 + dx * t0, x1 - dx, y1 - dx * t1, x1, y1);
}

function MonotoneX(context) {
  this._context = context;
}

MonotoneX.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x0 = this._x1 =
    this._y0 = this._y1 =
    this._t0 = NaN;
    this._point = 0;
  },
  lineEnd: function() {
    switch (this._point) {
      case 2: this._context.lineTo(this._x1, this._y1); break;
      case 3: monotone_point(this, this._t0, slope2(this, this._t0)); break;
    }
    if (this._line || (this._line !== 0 && this._point === 1)) this._context.closePath();
    this._line = 1 - this._line;
  },
  point: function(x, y) {
    var t1 = NaN;

    x = +x, y = +y;
    if (x === this._x1 && y === this._y1) return; // Ignore coincident points.
    switch (this._point) {
      case 0: this._point = 1; this._line ? this._context.lineTo(x, y) : this._context.moveTo(x, y); break;
      case 1: this._point = 2; break;
      case 2: this._point = 3; monotone_point(this, slope2(this, t1 = slope3(this, x, y)), t1); break;
      default: monotone_point(this, this._t0, t1 = slope3(this, x, y)); break;
    }

    this._x0 = this._x1, this._x1 = x;
    this._y0 = this._y1, this._y1 = y;
    this._t0 = t1;
  }
}

function MonotoneY(context) {
  this._context = new ReflectContext(context);
}

(MonotoneY.prototype = Object.create(MonotoneX.prototype)).point = function(x, y) {
  MonotoneX.prototype.point.call(this, y, x);
};

function ReflectContext(context) {
  this._context = context;
}

ReflectContext.prototype = {
  moveTo: function(x, y) { this._context.moveTo(y, x); },
  closePath: function() { this._context.closePath(); },
  lineTo: function(x, y) { this._context.lineTo(y, x); },
  bezierCurveTo: function(x1, y1, x2, y2, x, y) { this._context.bezierCurveTo(y1, x1, y2, x2, y, x); }
};

function monotoneX(context) {
  return new MonotoneX(context);
}

function monotoneY(context) {
  return new MonotoneY(context);
}

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/natural.js
function Natural(context) {
  this._context = context;
}

Natural.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x = [];
    this._y = [];
  },
  lineEnd: function() {
    var x = this._x,
        y = this._y,
        n = x.length;

    if (n) {
      this._line ? this._context.lineTo(x[0], y[0]) : this._context.moveTo(x[0], y[0]);
      if (n === 2) {
        this._context.lineTo(x[1], y[1]);
      } else {
        var px = controlPoints(x),
            py = controlPoints(y);
        for (var i0 = 0, i1 = 1; i1 < n; ++i0, ++i1) {
          this._context.bezierCurveTo(px[0][i0], py[0][i0], px[1][i0], py[1][i0], x[i1], y[i1]);
        }
      }
    }

    if (this._line || (this._line !== 0 && n === 1)) this._context.closePath();
    this._line = 1 - this._line;
    this._x = this._y = null;
  },
  point: function(x, y) {
    this._x.push(+x);
    this._y.push(+y);
  }
};

// See https://www.particleincell.com/2012/bezier-splines/ for derivation.
function controlPoints(x) {
  var i,
      n = x.length - 1,
      m,
      a = new Array(n),
      b = new Array(n),
      r = new Array(n);
  a[0] = 0, b[0] = 2, r[0] = x[0] + 2 * x[1];
  for (i = 1; i < n - 1; ++i) a[i] = 1, b[i] = 4, r[i] = 4 * x[i] + 2 * x[i + 1];
  a[n - 1] = 2, b[n - 1] = 7, r[n - 1] = 8 * x[n - 1] + x[n];
  for (i = 1; i < n; ++i) m = a[i] / b[i - 1], b[i] -= m, r[i] -= m * r[i - 1];
  a[n - 1] = r[n - 1] / b[n - 1];
  for (i = n - 2; i >= 0; --i) a[i] = (r[i] - a[i + 1]) / b[i];
  b[n - 1] = (x[n] + a[n - 1]) / 2;
  for (i = 0; i < n - 1; ++i) b[i] = 2 * x[i + 1] - a[i + 1];
  return [a, b];
}

/* harmony default export */ var natural = (function(context) {
  return new Natural(context);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/curve/step.js
function Step(context, t) {
  this._context = context;
  this._t = t;
}

Step.prototype = {
  areaStart: function() {
    this._line = 0;
  },
  areaEnd: function() {
    this._line = NaN;
  },
  lineStart: function() {
    this._x = this._y = NaN;
    this._point = 0;
  },
  lineEnd: function() {
    if (0 < this._t && this._t < 1 && this._point === 2) this._context.lineTo(this._x, this._y);
    if (this._line || (this._line !== 0 && this._point === 1)) this._context.closePath();
    if (this._line >= 0) this._t = 1 - this._t, this._line = 1 - this._line;
  },
  point: function(x, y) {
    x = +x, y = +y;
    switch (this._point) {
      case 0: this._point = 1; this._line ? this._context.lineTo(x, y) : this._context.moveTo(x, y); break;
      case 1: this._point = 2; // proceed
      default: {
        if (this._t <= 0) {
          this._context.lineTo(this._x, y);
          this._context.lineTo(x, y);
        } else {
          var x1 = this._x * (1 - this._t) + x * this._t;
          this._context.lineTo(x1, this._y);
          this._context.lineTo(x1, y);
        }
        break;
      }
    }
    this._x = x, this._y = y;
  }
};

/* harmony default export */ var step = (function(context) {
  return new Step(context, 0.5);
});

function stepBefore(context) {
  return new Step(context, 0);
}

function stepAfter(context) {
  return new Step(context, 1);
}

// CONCATENATED MODULE: ./node_modules/d3-shape/src/offset/none.js
/* harmony default export */ var offset_none = (function(series, order) {
  if (!((n = series.length) > 1)) return;
  for (var i = 1, j, s0, s1 = series[order[0]], n, m = s1.length; i < n; ++i) {
    s0 = s1, s1 = series[order[i]];
    for (j = 0; j < m; ++j) {
      s1[j][1] += s1[j][0] = isNaN(s0[j][1]) ? s0[j][0] : s0[j][1];
    }
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/order/none.js
/* harmony default export */ var order_none = (function(series) {
  var n = series.length, o = new Array(n);
  while (--n >= 0) o[n] = n;
  return o;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/stack.js





function stackValue(d, key) {
  return d[key];
}

/* harmony default export */ var src_stack = (function() {
  var keys = d3_shape_src_constant([]),
      order = order_none,
      offset = offset_none,
      value = stackValue;

  function stack(data) {
    var kz = keys.apply(this, arguments),
        i,
        m = data.length,
        n = kz.length,
        sz = new Array(n),
        oz;

    for (i = 0; i < n; ++i) {
      for (var ki = kz[i], si = sz[i] = new Array(m), j = 0, sij; j < m; ++j) {
        si[j] = sij = [0, +value(data[j], ki, j, data)];
        sij.data = data[j];
      }
      si.key = ki;
    }

    for (i = 0, oz = order(sz); i < n; ++i) {
      sz[oz[i]].index = i;
    }

    offset(sz, oz);
    return sz;
  }

  stack.keys = function(_) {
    return arguments.length ? (keys = typeof _ === "function" ? _ : d3_shape_src_constant(array_slice.call(_)), stack) : keys;
  };

  stack.value = function(_) {
    return arguments.length ? (value = typeof _ === "function" ? _ : d3_shape_src_constant(+_), stack) : value;
  };

  stack.order = function(_) {
    return arguments.length ? (order = _ == null ? order_none : typeof _ === "function" ? _ : d3_shape_src_constant(array_slice.call(_)), stack) : order;
  };

  stack.offset = function(_) {
    return arguments.length ? (offset = _ == null ? offset_none : _, stack) : offset;
  };

  return stack;
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/offset/expand.js


/* harmony default export */ var expand = (function(series, order) {
  if (!((n = series.length) > 0)) return;
  for (var i, n, j = 0, m = series[0].length, y; j < m; ++j) {
    for (y = i = 0; i < n; ++i) y += series[i][j][1] || 0;
    if (y) for (i = 0; i < n; ++i) series[i][j][1] /= y;
  }
  offset_none(series, order);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/offset/diverging.js
/* harmony default export */ var diverging = (function(series, order) {
  if (!((n = series.length) > 1)) return;
  for (var i, j = 0, d, dy, yp, yn, n, m = series[order[0]].length; j < m; ++j) {
    for (yp = yn = 0, i = 0; i < n; ++i) {
      if ((dy = (d = series[order[i]][j])[1] - d[0]) >= 0) {
        d[0] = yp, d[1] = yp += dy;
      } else if (dy < 0) {
        d[1] = yn, d[0] = yn += dy;
      } else {
        d[0] = yp;
      }
    }
  }
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/offset/silhouette.js


/* harmony default export */ var silhouette = (function(series, order) {
  if (!((n = series.length) > 0)) return;
  for (var j = 0, s0 = series[order[0]], n, m = s0.length; j < m; ++j) {
    for (var i = 0, y = 0; i < n; ++i) y += series[i][j][1] || 0;
    s0[j][1] += s0[j][0] = -y / 2;
  }
  offset_none(series, order);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/offset/wiggle.js


/* harmony default export */ var wiggle = (function(series, order) {
  if (!((n = series.length) > 0) || !((m = (s0 = series[order[0]]).length) > 0)) return;
  for (var y = 0, j = 1, s0, m, n; j < m; ++j) {
    for (var i = 0, s1 = 0, s2 = 0; i < n; ++i) {
      var si = series[order[i]],
          sij0 = si[j][1] || 0,
          sij1 = si[j - 1][1] || 0,
          s3 = (sij0 - sij1) / 2;
      for (var k = 0; k < i; ++k) {
        var sk = series[order[k]],
            skj0 = sk[j][1] || 0,
            skj1 = sk[j - 1][1] || 0;
        s3 += skj0 - skj1;
      }
      s1 += sij0, s2 += s3 * sij0;
    }
    s0[j - 1][1] += s0[j - 1][0] = y;
    if (s1) y -= s2 / s1;
  }
  s0[j - 1][1] += s0[j - 1][0] = y;
  offset_none(series, order);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/order/appearance.js


/* harmony default export */ var appearance = (function(series) {
  var peaks = series.map(peak);
  return order_none(series).sort(function(a, b) { return peaks[a] - peaks[b]; });
});

function peak(series) {
  var i = -1, j = 0, n = series.length, vi, vj = -Infinity;
  while (++i < n) if ((vi = +series[i][1]) > vj) vj = vi, j = i;
  return j;
}

// CONCATENATED MODULE: ./node_modules/d3-shape/src/order/ascending.js


/* harmony default export */ var order_ascending = (function(series) {
  var sums = series.map(ascending_sum);
  return order_none(series).sort(function(a, b) { return sums[a] - sums[b]; });
});

function ascending_sum(series) {
  var s = 0, i = -1, n = series.length, v;
  while (++i < n) if (v = +series[i][1]) s += v;
  return s;
}

// CONCATENATED MODULE: ./node_modules/d3-shape/src/order/descending.js


/* harmony default export */ var order_descending = (function(series) {
  return order_ascending(series).reverse();
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/order/insideOut.js



/* harmony default export */ var insideOut = (function(series) {
  var n = series.length,
      i,
      j,
      sums = series.map(ascending_sum),
      order = appearance(series),
      top = 0,
      bottom = 0,
      tops = [],
      bottoms = [];

  for (i = 0; i < n; ++i) {
    j = order[i];
    if (top < bottom) {
      top += sums[j];
      tops.push(j);
    } else {
      bottom += sums[j];
      bottoms.push(j);
    }
  }

  return bottoms.reverse().concat(tops);
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/order/reverse.js


/* harmony default export */ var reverse = (function(series) {
  return order_none(series).reverse();
});

// CONCATENATED MODULE: ./node_modules/d3-shape/src/index.js




 // Note: radialArea is deprecated!
 // Note: radialLine is deprecated!









































// CONCATENATED MODULE: ./src/js/CustomD3.js
function _objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; var ownKeys = Object.keys(source); if (typeof Object.getOwnPropertySymbols === 'function') { ownKeys = ownKeys.concat(Object.getOwnPropertySymbols(source).filter(function (sym) { return Object.getOwnPropertyDescriptor(source, sym).enumerable; })); } ownKeys.forEach(function (key) { _defineProperty(target, key, source[key]); }); } return target; }

function _defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

/**
 * We only import the necessary modules
 * from D3, to keep resulting bundded
 * JS files minimal in size.
 */



 // create a Object with only the subset of functions/submodules/plugins that we need

var d3 = _objectSpread({
  select: src_select,
  selectAll: src_selectAll,

  // For more information on live bindings, refer to:
  //   https://stackoverflow.com/questions/40012016/importing-d3-event-into-a-custom-build-using-rollup
  get event() {
    return on_event;
  },

  linkHorizontal: linkHorizontal
}, d3_hierarchy_src_namespaceObject, d3_zoom_src_namespaceObject);

/* harmony default export */ var CustomD3 = (d3);
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/textWidth.js
/**
    @function textWidth
    @desc Given a text string, returns the predicted pixel width of the string when placed into DOM.
    @param {String|Array} text Can be either a single string or an array of strings to analyze.
    @param {Object} [style] An object of CSS font styles to apply. Accepts any of the valid [CSS font property](http://www.w3schools.com/cssref/pr_font_font.asp) values.
*/
/* harmony default export */ var textWidth = (function(text, style) {

  style = Object.assign({
    "font-size": 10,
    "font-family": "sans-serif",
    "font-style": "normal",
    "font-weight": 400,
    "font-variant": "normal"
  }, style);

  var context = document.createElement("canvas").getContext("2d");

  var font = [];
  font.push(style["font-style"]);
  font.push(style["font-variant"]);
  font.push(style["font-weight"]);
  font.push(typeof style["font-size"] === "string" ? style["font-size"] : ((style["font-size"]) + "px"));
  // let s = `${style["font-size"]}px`;
  // if ("line-height" in style) s += `/${style["line-height"]}px`;
  // font.push(s);
  font.push(style["font-family"]);

  context.font = font.join(" ");

  if (text instanceof Array) { return text.map(function (t) { return context.measureText(t).width; }); }
  return context.measureText(text).width;

});

//# sourceMappingURL=textWidth.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/trim.js
/**
    @function trim
    @desc Cross-browser implementation of [trim](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/Trim).
    @param {String} str
*/
function trim(str) {
  return str.replace(/^\s+|\s+$/g, "");
}

/**
    @function trimLeft
    @desc Cross-browser implementation of [trimLeft](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/TrimLeft).
    @param {String} str
*/
function trimLeft(str) {
  return str.replace(/^\s+/, "");
}

/**
    @function trimRight
    @desc Cross-browser implementation of [trimRight](https://developer.mozilla.org/en-US/docs/Web/JavaScript/Reference/Global_Objects/String/TrimRight).
    @param {String} str
*/
function trimRight(str) {
  return str.replace(/\s+$/, "");
}



//# sourceMappingURL=trim.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/fontExists.js



var fontExists_alpha = "abcdefghiABCDEFGHI_!@#$%^&*()_+1234567890",
      checked = {},
      fontExists_height = 32;

var dejavu, macos, monospace, proportional;

/**
    @function fontExists
    @desc Given either a single font-family or a list of fonts, returns the name of the first font that can be rendered, or `false` if none are installed on the user's machine.
    @param {String|Array} font Can be either a valid CSS font-family string (single or comma-separated names) or an Array of string names.
*/
var fontExists = function (font) {

  if (!dejavu) {
    dejavu = textWidth(fontExists_alpha, {"font-family": "DejaVuSans", "font-size": fontExists_height});
    macos = textWidth(fontExists_alpha, {"font-family": "-apple-system", "font-size": fontExists_height});
    monospace = textWidth(fontExists_alpha, {"font-family": "monospace", "font-size": fontExists_height});
    proportional = textWidth(fontExists_alpha, {"font-family": "sans-serif", "font-size": fontExists_height});
  }

  if (!(font instanceof Array)) { font = font.split(","); }
  font = font.map(function (f) { return trim(f); });

  for (var i = 0; i < font.length; i++) {
    var fam = font[i];
    if (checked[fam] || ["-apple-system", "monospace", "sans-serif", "DejaVuSans"].includes(fam)) { return fam; }
    else if (checked[fam] === false) { continue; }
    var width = textWidth(fontExists_alpha, {"font-family": fam, "font-size": fontExists_height});
    checked[fam] = width !== monospace;
    if (checked[fam]) { checked[fam] = width !== proportional; }
    if (macos && checked[fam]) { checked[fam] = width !== macos; }
    if (dejavu && checked[fam]) { checked[fam] = width !== dejavu; }
    if (checked[fam]) { return fam; }
  }

  return false;

};


/* harmony default export */ var src_fontExists = (fontExists);

//# sourceMappingURL=fontExists.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/rtl.js


/**
    @function rtl
    @desc Returns `true` if the HTML or body element has either the "dir" HTML attribute or the "direction" CSS property set to "rtl".
*/
/* harmony default export */ var src_rtl = (function () { return src_select("html").attr("dir") === "rtl" ||
  src_select("body").attr("dir") === "rtl" ||
  src_select("html").style("direction") === "rtl" ||
  src_select("body").style("direction") === "rtl"; });;

//# sourceMappingURL=rtl.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/stringify.js
/**
    @function stringify
    @desc Coerces value into a String.
    @param {String} value
*/
/* harmony default export */ var stringify = (function(value) {
  if (value === void 0) { value = "undefined"; }
  else if (!(typeof value === "string" || value instanceof String)) { value = JSON.stringify(value); }
  return value;
});

//# sourceMappingURL=stringify.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/strip.js
// great unicode list: http://asecuritysite.com/coding/asc2

var diacritics = [
  [/[\300-\305]/g, "A"], [/[\340-\345]/g, "a"],
  [/[\306]/g, "AE"], [/[\346]/g, "ae"],
  [/[\337]/g, "B"],
  [/[\307]/g, "C"], [/[\347]/g, "c"],
  [/[\320\336\376]/g, "D"], [/[\360]/g, "d"],
  [/[\310-\313]/g, "E"], [/[\350-\353]/g, "e"],
  [/[\314-\317]/g, "I"], [/[\354-\357]/g, "i"],
  [/[\321]/g, "N"], [/[\361]/g, "n"],
  [/[\322-\326\330]/g, "O"], [/[\362-\366\370]/g, "o"],
  [/[\331-\334]/g, "U"], [/[\371-\374]/g, "u"],
  [/[\327]/g, "x"],
  [/[\335]/g, "Y"], [/[\375\377]/g, "y"]
];

/**
    @function strip
    @desc Removes all non ASCII characters from a string.
    @param {String} value
*/
/* harmony default export */ var strip = (function(value) {

  return ("" + value).replace(/[^A-Za-z0-9\-_]/g, function (char) {

    if (char === " ") { return "-"; }

    var ret = false;
    for (var d = 0; d < diacritics.length; d++) {
      if (new RegExp(diacritics[d][0]).test(char)) {
        ret = diacritics[d][1];
        break;
      }
    }

    return ret || "";

  });
});

//# sourceMappingURL=strip.js.map
// CONCATENATED MODULE: ./node_modules/d3-array/src/ascending.js
/* harmony default export */ var src_ascending = (function(a, b) {
  return a < b ? -1 : a > b ? 1 : a >= b ? 0 : NaN;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/bisector.js


/* harmony default export */ var bisector = (function(compare) {
  if (compare.length === 1) compare = ascendingComparator(compare);
  return {
    left: function(a, x, lo, hi) {
      if (lo == null) lo = 0;
      if (hi == null) hi = a.length;
      while (lo < hi) {
        var mid = lo + hi >>> 1;
        if (compare(a[mid], x) < 0) lo = mid + 1;
        else hi = mid;
      }
      return lo;
    },
    right: function(a, x, lo, hi) {
      if (lo == null) lo = 0;
      if (hi == null) hi = a.length;
      while (lo < hi) {
        var mid = lo + hi >>> 1;
        if (compare(a[mid], x) > 0) hi = mid;
        else lo = mid + 1;
      }
      return lo;
    }
  };
});

function ascendingComparator(f) {
  return function(d, x) {
    return src_ascending(f(d), x);
  };
}

// CONCATENATED MODULE: ./node_modules/d3-array/src/bisect.js



var ascendingBisect = bisector(src_ascending);
var bisectRight = ascendingBisect.right;
var bisectLeft = ascendingBisect.left;
/* harmony default export */ var bisect = (bisectRight);

// CONCATENATED MODULE: ./node_modules/d3-array/src/pairs.js
/* harmony default export */ var pairs = (function(array, f) {
  if (f == null) f = pair;
  var i = 0, n = array.length - 1, p = array[0], pairs = new Array(n < 0 ? 0 : n);
  while (i < n) pairs[i] = f(p, p = array[++i]);
  return pairs;
});

function pair(a, b) {
  return [a, b];
}

// CONCATENATED MODULE: ./node_modules/d3-array/src/cross.js


/* harmony default export */ var src_cross = (function(values0, values1, reduce) {
  var n0 = values0.length,
      n1 = values1.length,
      values = new Array(n0 * n1),
      i0,
      i1,
      i,
      value0;

  if (reduce == null) reduce = pair;

  for (i0 = i = 0; i0 < n0; ++i0) {
    for (value0 = values0[i0], i1 = 0; i1 < n1; ++i1, ++i) {
      values[i] = reduce(value0, values1[i1]);
    }
  }

  return values;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/descending.js
/* harmony default export */ var src_descending = (function(a, b) {
  return b < a ? -1 : b > a ? 1 : b >= a ? 0 : NaN;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/number.js
/* harmony default export */ var src_number = (function(x) {
  return x === null ? NaN : +x;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/variance.js


/* harmony default export */ var variance = (function(values, valueof) {
  var n = values.length,
      m = 0,
      i = -1,
      mean = 0,
      value,
      delta,
      sum = 0;

  if (valueof == null) {
    while (++i < n) {
      if (!isNaN(value = src_number(values[i]))) {
        delta = value - mean;
        mean += delta / ++m;
        sum += delta * (value - mean);
      }
    }
  }

  else {
    while (++i < n) {
      if (!isNaN(value = src_number(valueof(values[i], i, values)))) {
        delta = value - mean;
        mean += delta / ++m;
        sum += delta * (value - mean);
      }
    }
  }

  if (m > 1) return sum / (m - 1);
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/deviation.js


/* harmony default export */ var deviation = (function(array, f) {
  var v = variance(array, f);
  return v ? Math.sqrt(v) : v;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/extent.js
/* harmony default export */ var src_extent = (function(values, valueof) {
  var n = values.length,
      i = -1,
      value,
      min,
      max;

  if (valueof == null) {
    while (++i < n) { // Find the first comparable value.
      if ((value = values[i]) != null && value >= value) {
        min = max = value;
        while (++i < n) { // Compare the remaining values.
          if ((value = values[i]) != null) {
            if (min > value) min = value;
            if (max < value) max = value;
          }
        }
      }
    }
  }

  else {
    while (++i < n) { // Find the first comparable value.
      if ((value = valueof(values[i], i, values)) != null && value >= value) {
        min = max = value;
        while (++i < n) { // Compare the remaining values.
          if ((value = valueof(values[i], i, values)) != null) {
            if (min > value) min = value;
            if (max < value) max = value;
          }
        }
      }
    }
  }

  return [min, max];
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/array.js
var array_array = Array.prototype;

var src_array_slice = array_array.slice;
var map = array_array.map;

// CONCATENATED MODULE: ./node_modules/d3-array/src/constant.js
/* harmony default export */ var d3_array_src_constant = (function(x) {
  return function() {
    return x;
  };
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/identity.js
/* harmony default export */ var d3_array_src_identity = (function(x) {
  return x;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/range.js
/* harmony default export */ var range = (function(start, stop, step) {
  start = +start, stop = +stop, step = (n = arguments.length) < 2 ? (stop = start, start = 0, 1) : n < 3 ? 1 : +step;

  var i = -1,
      n = Math.max(0, Math.ceil((stop - start) / step)) | 0,
      range = new Array(n);

  while (++i < n) {
    range[i] = start + i * step;
  }

  return range;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/ticks.js
var e10 = Math.sqrt(50),
    e5 = Math.sqrt(10),
    e2 = Math.sqrt(2);

/* harmony default export */ var ticks = (function(start, stop, count) {
  var reverse,
      i = -1,
      n,
      ticks,
      step;

  stop = +stop, start = +start, count = +count;
  if (start === stop && count > 0) return [start];
  if (reverse = stop < start) n = start, start = stop, stop = n;
  if ((step = tickIncrement(start, stop, count)) === 0 || !isFinite(step)) return [];

  if (step > 0) {
    start = Math.ceil(start / step);
    stop = Math.floor(stop / step);
    ticks = new Array(n = Math.ceil(stop - start + 1));
    while (++i < n) ticks[i] = (start + i) * step;
  } else {
    start = Math.floor(start * step);
    stop = Math.ceil(stop * step);
    ticks = new Array(n = Math.ceil(start - stop + 1));
    while (++i < n) ticks[i] = (start - i) / step;
  }

  if (reverse) ticks.reverse();

  return ticks;
});

function tickIncrement(start, stop, count) {
  var step = (stop - start) / Math.max(0, count),
      power = Math.floor(Math.log(step) / Math.LN10),
      error = step / Math.pow(10, power);
  return power >= 0
      ? (error >= e10 ? 10 : error >= e5 ? 5 : error >= e2 ? 2 : 1) * Math.pow(10, power)
      : -Math.pow(10, -power) / (error >= e10 ? 10 : error >= e5 ? 5 : error >= e2 ? 2 : 1);
}

function tickStep(start, stop, count) {
  var step0 = Math.abs(stop - start) / Math.max(0, count),
      step1 = Math.pow(10, Math.floor(Math.log(step0) / Math.LN10)),
      error = step0 / step1;
  if (error >= e10) step1 *= 10;
  else if (error >= e5) step1 *= 5;
  else if (error >= e2) step1 *= 2;
  return stop < start ? -step1 : step1;
}

// CONCATENATED MODULE: ./node_modules/d3-array/src/threshold/sturges.js
/* harmony default export */ var sturges = (function(values) {
  return Math.ceil(Math.log(values.length) / Math.LN2) + 1;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/histogram.js









/* harmony default export */ var src_histogram = (function() {
  var value = d3_array_src_identity,
      domain = src_extent,
      threshold = sturges;

  function histogram(data) {
    var i,
        n = data.length,
        x,
        values = new Array(n);

    for (i = 0; i < n; ++i) {
      values[i] = value(data[i], i, data);
    }

    var xz = domain(values),
        x0 = xz[0],
        x1 = xz[1],
        tz = threshold(values, x0, x1);

    // Convert number of thresholds into uniform thresholds.
    if (!Array.isArray(tz)) {
      tz = tickStep(x0, x1, tz);
      tz = range(Math.ceil(x0 / tz) * tz, x1, tz); // exclusive
    }

    // Remove any thresholds outside the domain.
    var m = tz.length;
    while (tz[0] <= x0) tz.shift(), --m;
    while (tz[m - 1] > x1) tz.pop(), --m;

    var bins = new Array(m + 1),
        bin;

    // Initialize bins.
    for (i = 0; i <= m; ++i) {
      bin = bins[i] = [];
      bin.x0 = i > 0 ? tz[i - 1] : x0;
      bin.x1 = i < m ? tz[i] : x1;
    }

    // Assign data to bins by value, ignoring any outside the domain.
    for (i = 0; i < n; ++i) {
      x = values[i];
      if (x0 <= x && x <= x1) {
        bins[bisect(tz, x, 0, m)].push(data[i]);
      }
    }

    return bins;
  }

  histogram.value = function(_) {
    return arguments.length ? (value = typeof _ === "function" ? _ : d3_array_src_constant(_), histogram) : value;
  };

  histogram.domain = function(_) {
    return arguments.length ? (domain = typeof _ === "function" ? _ : d3_array_src_constant([_[0], _[1]]), histogram) : domain;
  };

  histogram.thresholds = function(_) {
    return arguments.length ? (threshold = typeof _ === "function" ? _ : Array.isArray(_) ? d3_array_src_constant(src_array_slice.call(_)) : d3_array_src_constant(_), histogram) : threshold;
  };

  return histogram;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/quantile.js


/* harmony default export */ var quantile = (function(values, p, valueof) {
  if (valueof == null) valueof = src_number;
  if (!(n = values.length)) return;
  if ((p = +p) <= 0 || n < 2) return +valueof(values[0], 0, values);
  if (p >= 1) return +valueof(values[n - 1], n - 1, values);
  var n,
      i = (n - 1) * p,
      i0 = Math.floor(i),
      value0 = +valueof(values[i0], i0, values),
      value1 = +valueof(values[i0 + 1], i0 + 1, values);
  return value0 + (value1 - value0) * (i - i0);
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/threshold/freedmanDiaconis.js





/* harmony default export */ var freedmanDiaconis = (function(values, min, max) {
  values = map.call(values, src_number).sort(src_ascending);
  return Math.ceil((max - min) / (2 * (quantile(values, 0.75) - quantile(values, 0.25)) * Math.pow(values.length, -1 / 3)));
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/threshold/scott.js


/* harmony default export */ var scott = (function(values, min, max) {
  return Math.ceil((max - min) / (3.5 * deviation(values) * Math.pow(values.length, -1 / 3)));
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/max.js
/* harmony default export */ var src_max = (function(values, valueof) {
  var n = values.length,
      i = -1,
      value,
      max;

  if (valueof == null) {
    while (++i < n) { // Find the first comparable value.
      if ((value = values[i]) != null && value >= value) {
        max = value;
        while (++i < n) { // Compare the remaining values.
          if ((value = values[i]) != null && value > max) {
            max = value;
          }
        }
      }
    }
  }

  else {
    while (++i < n) { // Find the first comparable value.
      if ((value = valueof(values[i], i, values)) != null && value >= value) {
        max = value;
        while (++i < n) { // Compare the remaining values.
          if ((value = valueof(values[i], i, values)) != null && value > max) {
            max = value;
          }
        }
      }
    }
  }

  return max;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/mean.js


/* harmony default export */ var src_mean = (function(values, valueof) {
  var n = values.length,
      m = n,
      i = -1,
      value,
      sum = 0;

  if (valueof == null) {
    while (++i < n) {
      if (!isNaN(value = src_number(values[i]))) sum += value;
      else --m;
    }
  }

  else {
    while (++i < n) {
      if (!isNaN(value = src_number(valueof(values[i], i, values)))) sum += value;
      else --m;
    }
  }

  if (m) return sum / m;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/median.js




/* harmony default export */ var median = (function(values, valueof) {
  var n = values.length,
      i = -1,
      value,
      numbers = [];

  if (valueof == null) {
    while (++i < n) {
      if (!isNaN(value = src_number(values[i]))) {
        numbers.push(value);
      }
    }
  }

  else {
    while (++i < n) {
      if (!isNaN(value = src_number(valueof(values[i], i, values)))) {
        numbers.push(value);
      }
    }
  }

  return quantile(numbers.sort(src_ascending), 0.5);
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/merge.js
/* harmony default export */ var src_merge = (function(arrays) {
  var n = arrays.length,
      m,
      i = -1,
      j = 0,
      merged,
      array;

  while (++i < n) j += arrays[i].length;
  merged = new Array(j);

  while (--n >= 0) {
    array = arrays[n];
    m = array.length;
    while (--m >= 0) {
      merged[--j] = array[m];
    }
  }

  return merged;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/min.js
/* harmony default export */ var src_min = (function(values, valueof) {
  var n = values.length,
      i = -1,
      value,
      min;

  if (valueof == null) {
    while (++i < n) { // Find the first comparable value.
      if ((value = values[i]) != null && value >= value) {
        min = value;
        while (++i < n) { // Compare the remaining values.
          if ((value = values[i]) != null && min > value) {
            min = value;
          }
        }
      }
    }
  }

  else {
    while (++i < n) { // Find the first comparable value.
      if ((value = valueof(values[i], i, values)) != null && value >= value) {
        min = value;
        while (++i < n) { // Compare the remaining values.
          if ((value = valueof(values[i], i, values)) != null && min > value) {
            min = value;
          }
        }
      }
    }
  }

  return min;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/permute.js
/* harmony default export */ var permute = (function(array, indexes) {
  var i = indexes.length, permutes = new Array(i);
  while (i--) permutes[i] = array[indexes[i]];
  return permutes;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/scan.js


/* harmony default export */ var scan = (function(values, compare) {
  if (!(n = values.length)) return;
  var n,
      i = 0,
      j = 0,
      xi,
      xj = values[j];

  if (compare == null) compare = src_ascending;

  while (++i < n) {
    if (compare(xi = values[i], xj) < 0 || compare(xj, xj) !== 0) {
      xj = xi, j = i;
    }
  }

  if (compare(xj, xj) === 0) return j;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/shuffle.js
/* harmony default export */ var src_shuffle = (function(array, i0, i1) {
  var m = (i1 == null ? array.length : i1) - (i0 = i0 == null ? 0 : +i0),
      t,
      i;

  while (m) {
    i = Math.random() * m-- | 0;
    t = array[m + i0];
    array[m + i0] = array[i + i0];
    array[i + i0] = t;
  }

  return array;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/sum.js
/* harmony default export */ var src_sum = (function(values, valueof) {
  var n = values.length,
      i = -1,
      value,
      sum = 0;

  if (valueof == null) {
    while (++i < n) {
      if (value = +values[i]) sum += value; // Note: zero and null are equivalent.
    }
  }

  else {
    while (++i < n) {
      if (value = +valueof(values[i], i, values)) sum += value;
    }
  }

  return sum;
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/transpose.js


/* harmony default export */ var src_transpose = (function(matrix) {
  if (!(n = matrix.length)) return [];
  for (var i = -1, m = src_min(matrix, transpose_length), transpose = new Array(m); ++i < m;) {
    for (var j = -1, n, row = transpose[i] = new Array(n); ++j < n;) {
      row[j] = matrix[j][i];
    }
  }
  return transpose;
});

function transpose_length(d) {
  return d.length;
}

// CONCATENATED MODULE: ./node_modules/d3-array/src/zip.js


/* harmony default export */ var zip = (function() {
  return src_transpose(arguments);
});

// CONCATENATED MODULE: ./node_modules/d3-array/src/index.js




























// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/accessor.js
/**
    @function accessor
    @desc Wraps an object key in a simple accessor function.
    @param {String} key The key to be returned from each Object passed to the function.
    @param {*} [def] A default value to be returned if the key is not present.
    @example <caption>this</caption>
accessor("id");
    @example <caption>returns this</caption>
function(d) {
  return d["id"];
}
*/
/* harmony default export */ var accessor = (function(key, def) {
  if (def === void 0) { return function (d) { return d[key]; }; }
  return function (d) { return d[key] === void 0 ? def : d[key]; };
});

//# sourceMappingURL=accessor.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/isObject.js
/**
    @function isObject
    @desc Detects if a variable is a javascript Object.
    @param {*} item
*/
/* harmony default export */ var isObject = (function(item) {
  return item &&
    typeof item === "object" &&
    (typeof window === "undefined" || item !== window && item !== window.document && !(item instanceof Element)) &&
    !Array.isArray(item)
    ? true : false;
});

//# sourceMappingURL=isObject.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/assign.js


/**
    @function validObject
    @desc Determines if the object passed is the document or window.
    @param {Object} obj
    @private
*/
function validObject(obj) {
  if (typeof window === "undefined") { return true; }
  else { return obj !== window && obj !== document; }
}

/**
    @function assign
    @desc A deeply recursive version of `Object.assign`.
    @param {...Object} objects
    @example <caption>this</caption>
assign({id: "foo", deep: {group: "A"}}, {id: "bar", deep: {value: 20}}));
    @example <caption>returns this</caption>
{id: "bar", deep: {group: "A", value: 20}}
*/
function assign_assign() {
  var objects = [], len = arguments.length;
  while ( len-- ) objects[ len ] = arguments[ len ];


  var target = objects[0];
  var loop = function ( i ) {

    var source = objects[i];

    Object.keys(source).forEach(function (prop) {

      var value = source[prop];

      if (isObject(value) && validObject(value)) {
        if (target.hasOwnProperty(prop) && isObject(target[prop])) { target[prop] = assign_assign({}, target[prop], value); }
        else { target[prop] = assign_assign({}, value); }
      }
      else if (Array.isArray(value)) { target[prop] = value.slice(); }
      else { target[prop] = value; }

    });
  };

  for (var i = 1; i < objects.length; i++) loop( i );

  return target;

}

/* harmony default export */ var src_assign = (assign_assign);

//# sourceMappingURL=assign.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/attrize.js
/**
    @function attrize
    @desc Applies each key/value in an object as an attr.
    @param {D3selection} elem The D3 element to apply the styles to.
    @param {Object} attrs An object of key/value attr pairs.
*/
/* harmony default export */ var attrize = (function(e, a) {
  if ( a === void 0 ) a = {};

  for (var k in a) { if ({}.hasOwnProperty.call(a, k)) { e.attr(k, a[k]); } }
});

//# sourceMappingURL=attrize.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/uuid.js
/**
    @function s
    @desc Returns 4 random characters, used for constructing unique identifiers.
    @private
*/
function uuid_s() {
  return Math.floor((1 + Math.random()) * 0x10000).toString(16).substring(1);
}

/**
    @function uuid
    @summary Returns a unique identifier.
*/
/* harmony default export */ var uuid = (function() {
  return ("" + (uuid_s()) + (uuid_s()) + "-" + (uuid_s()) + "-" + (uuid_s()) + "-" + (uuid_s()) + "-" + (uuid_s()) + (uuid_s()) + (uuid_s()));
});

//# sourceMappingURL=uuid.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/RESET.js
/**
    @constant RESET
    @desc String constant used to reset an individual config property.
*/
/* harmony default export */ var RESET = ("D3PLUS-COMMON-RESET");

//# sourceMappingURL=RESET.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/BaseClass.js





/**
    @desc Recursive function that resets nested Object configs.
    @param {Object} obj
    @param {Object} defaults
    @private
*/
function nestedReset(obj, defaults) {
  if (isObject(obj)) {
    for (var nestedKey in obj) {
      if ({}.hasOwnProperty.call(obj, nestedKey) && !nestedKey.startsWith("_")) {
        var defaultValue = defaults && isObject(defaults) ? defaults[nestedKey] : undefined;
        if (obj[nestedKey] === RESET) {
          obj[nestedKey] = defaultValue;
        }
        else if (isObject(obj[nestedKey])) {
          nestedReset(obj[nestedKey], defaultValue);
        }
      }
    }
  }
}

/**
    @class BaseClass
    @summary An abstract class that contains some global methods and functionality.
*/
var BaseClass_BaseClass = function BaseClass() {
  this._on = {};
  this._uuid = uuid();
};

/**
    @memberof BaseClass
    @desc If *value* is specified, sets the methods that correspond to the key/value pairs and returns this class. If *value* is not specified, returns the current configuration.
    @param {Object} [*value*]
    @chainable
*/
BaseClass_BaseClass.prototype.config = function config (_) {
    var this$1 = this;

  if (!this._configDefault) {
    var config = {};
    for (var k in this$1.__proto__) {
      if (k.indexOf("_") !== 0 && !["config", "constructor", "render"].includes(k)) {
        var v = this$1[k]();
        config[k] = isObject(v) ? src_assign({}, v) : v;
      }
    }
    this._configDefault = config;
  }
  if (arguments.length) {
    for (var k$1 in _) {
      if ({}.hasOwnProperty.call(_, k$1) && k$1 in this$1) {
        var v$1 = _[k$1];
        if (v$1 === RESET) {
          if (k$1 === "on") { this$1._on = this$1._configDefault[k$1]; }
          else { this$1[k$1](this$1._configDefault[k$1]); }
        }
        else {
          nestedReset(v$1, this$1._configDefault[k$1]);
          this$1[k$1](v$1);
        }
      }
    }
    return this;
  }
  else {
    var config$1 = {};
    for (var k$2 in this$1.__proto__) { if (k$2.indexOf("_") !== 0 && !["config", "constructor", "render"].includes(k$2)) { config$1[k$2] = this$1[k$2](); } }
    return config$1;
  }
};

/**
    @memberof BaseClass
    @desc Adds or removes a *listener* to each object for the specified event *typenames*. If a *listener* is not specified, returns the currently assigned listener for the specified event *typename*. Mirrors the core [d3-selection](https://github.com/d3/d3-selection#selection_on) behavior.
    @param {String} [*typenames*]
    @param {Function} [*listener*]
    @chainable
    @example <caption>By default, listeners apply globally to all objects, however, passing a namespace with the class name gives control over specific elements:</caption>
new Plot
.on("click.Shape", function(d) {
  console.log("data for shape clicked:", d);
})
.on("click.Legend", function(d) {
  console.log("data for legend clicked:", d);
})
*/
BaseClass_BaseClass.prototype.on = function on (_, f) {
  return arguments.length === 2 ? (this._on[_] = f, this) : arguments.length ? typeof _ === "string" ? this._on[_] : (this._on = Object.assign({}, this._on, _), this) : this._on;
};

/* harmony default export */ var src_BaseClass = (BaseClass_BaseClass);

//# sourceMappingURL=BaseClass.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/closest.js
/**
    @function closest
    @desc Finds the closest numeric value in an array.
    @param {Number} n The number value to use when searching the array.
    @param {Array} arr The array of values to test against.
*/
/* harmony default export */ var closest = (function(n, arr) {
  if ( arr === void 0 ) arr = [];

  if (!arr || !(arr instanceof Array) || !arr.length) { return undefined; }
  return arr.reduce(function (prev, curr) { return Math.abs(curr - n) < Math.abs(prev - n) ? curr : prev; });
});

//# sourceMappingURL=closest.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/configPrep.js
/**
    @function configPrep
    @desc Preps a config object for d3plus data, and optionally bubbles up a specific nested type. When using this function, you must bind a d3plus class' `this` context.
    @param {Object} [config = this._shapeConfig] The configuration object to parse.
    @param {String} [type = "shape"] The event classifier to user for "on" events. For example, the default event type of "shape" will apply all events in the "on" config object with that key, like "click.shape" and "mouseleave.shape", in addition to any gloval events like "click" and "mouseleave".
    @param {String} [nest] An optional nested key to bubble up to the parent config level.
*/
function configPrep(config, type, nest) {
  var this$1 = this;
  if ( config === void 0 ) config = this._shapeConfig;
  if ( type === void 0 ) type = "shape";
  if ( nest === void 0 ) nest = false;


  var newConfig = {duration: this._duration, on: {}};

  var wrapFunction = function (func) { return function (d, i, s) {
    while (d.__d3plus__) {
      i = d.i;
      d = d.data || d.feature;
    }
    return func.bind(this$1)(d, i, s);
  }; };

  var parseEvents = function (newObj, on) {

    for (var event in on) {

      if ({}.hasOwnProperty.call(on, event) && !event.includes(".") || event.includes(("." + type))) {
        newObj.on[event] = wrapFunction(on[event]);
      }

    }

  };

  var keyEval = function (newObj, obj) {

    for (var key in obj) {

      if ({}.hasOwnProperty.call(obj, key)) {

        if (key === "on") { parseEvents(newObj, obj[key]); }
        else if (typeof obj[key] === "function") {
          newObj[key] = wrapFunction(obj[key]);
        }
        else if (typeof obj[key] === "object" && !(obj instanceof Array)) {
          newObj[key] = {on: {}};
          keyEval(newObj[key], obj[key]);
        }
        else { newObj[key] = obj[key]; }

      }

    }

  };

  keyEval(newConfig, config);
  if (this._on) { parseEvents(newConfig, this._on); }
  if (nest && config[nest]) {
    keyEval(newConfig, config[nest]);
    if (config[nest].on) { parseEvents(newConfig, config[nest].on); }
  }

  return newConfig;

}

//# sourceMappingURL=configPrep.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/constant.js
/**
    @function constant
    @desc Wraps non-function variables in a simple return function.
    @param {Array|Number|Object|String} value The value to be returned from the function.
    @example <caption>this</caption>
constant(42);
    @example <caption>returns this</caption>
function() {
  return 42;
}
*/
/* harmony default export */ var es_src_constant = (function(value) {
  return function constant() {
    return value;
  };
});

//# sourceMappingURL=constant.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/elem.js





/**
    @function elem
    @desc Manages the enter/update/exit pattern for a single DOM element.
    @param {String} selector A D3 selector, which must include the tagname and a class and/or ID.
    @param {Object} params Additional parameters.
    @param {Boolean} [params.condition = true] Whether or not the element should be rendered (or removed).
    @param {Object} [params.enter = {}] A collection of key/value pairs that map to attributes to be given on enter.
    @param {Object} [params.exit = {}] A collection of key/value pairs that map to attributes to be given on exit.
    @param {D3Selection} [params.parent = d3.select("body")] The parent element for this new element to be appended to.
    @param {D3Transition} [params.transition = d3.transition().duration(0)] The transition to use when animated the different life cycle stages.
    @param {Object} [params.update = {}] A collection of key/value pairs that map to attributes to be given on update.
*/
/* harmony default export */ var src_elem = (function(selector, p) {

  // overrides default params
  p = Object.assign({}, {
    condition: true,
    enter: {},
    exit: {},
    parent: src_select("body"),
    transition: src_transition_transition().duration(0),
    update: {}
  }, p);

  var className = (/\.([^#]+)/g).exec(selector),
        id = (/#([^\.]+)/g).exec(selector),
        tag = (/^([^.^#]+)/g).exec(selector)[1];

  var elem = p.parent.selectAll(selector.includes(":") ? selector.split(":")[1] : selector)
    .data(p.condition ? [null] : []);

  var enter = elem.enter().append(tag).call(attrize, p.enter);

  if (id) { enter.attr("id", id[1]); }
  if (className) { enter.attr("class", className[1]); }

  elem.exit().transition(p.transition).call(attrize, p.exit).remove();

  var update = enter.merge(elem);
  update.transition(p.transition).call(attrize, p.update);

  return update;

});

//# sourceMappingURL=elem.js.map
// CONCATENATED MODULE: ./node_modules/d3-collection/src/map.js
var map_prefix = "$";

function Map() {}

Map.prototype = map_map.prototype = {
  constructor: Map,
  has: function(key) {
    return (map_prefix + key) in this;
  },
  get: function(key) {
    return this[map_prefix + key];
  },
  set: function(key, value) {
    this[map_prefix + key] = value;
    return this;
  },
  remove: function(key) {
    var property = map_prefix + key;
    return property in this && delete this[property];
  },
  clear: function() {
    for (var property in this) if (property[0] === map_prefix) delete this[property];
  },
  keys: function() {
    var keys = [];
    for (var property in this) if (property[0] === map_prefix) keys.push(property.slice(1));
    return keys;
  },
  values: function() {
    var values = [];
    for (var property in this) if (property[0] === map_prefix) values.push(this[property]);
    return values;
  },
  entries: function() {
    var entries = [];
    for (var property in this) if (property[0] === map_prefix) entries.push({key: property.slice(1), value: this[property]});
    return entries;
  },
  size: function() {
    var size = 0;
    for (var property in this) if (property[0] === map_prefix) ++size;
    return size;
  },
  empty: function() {
    for (var property in this) if (property[0] === map_prefix) return false;
    return true;
  },
  each: function(f) {
    for (var property in this) if (property[0] === map_prefix) f(this[property], property.slice(1), this);
  }
};

function map_map(object, f) {
  var map = new Map;

  // Copy constructor.
  if (object instanceof Map) object.each(function(value, key) { map.set(key, value); });

  // Index array by numeric index or specified key function.
  else if (Array.isArray(object)) {
    var i = -1,
        n = object.length,
        o;

    if (f == null) while (++i < n) map.set(i, object[i]);
    else while (++i < n) map.set(f(o = object[i], i, object), o);
  }

  // Convert object to map.
  else if (object) for (var key in object) map.set(key, object[key]);

  return map;
}

/* harmony default export */ var src_map = (map_map);

// CONCATENATED MODULE: ./node_modules/d3-collection/src/nest.js


/* harmony default export */ var src_nest = (function() {
  var keys = [],
      sortKeys = [],
      sortValues,
      rollup,
      nest;

  function apply(array, depth, createResult, setResult) {
    if (depth >= keys.length) {
      if (sortValues != null) array.sort(sortValues);
      return rollup != null ? rollup(array) : array;
    }

    var i = -1,
        n = array.length,
        key = keys[depth++],
        keyValue,
        value,
        valuesByKey = src_map(),
        values,
        result = createResult();

    while (++i < n) {
      if (values = valuesByKey.get(keyValue = key(value = array[i]) + "")) {
        values.push(value);
      } else {
        valuesByKey.set(keyValue, [value]);
      }
    }

    valuesByKey.each(function(values, key) {
      setResult(result, key, apply(values, depth, createResult, setResult));
    });

    return result;
  }

  function entries(map, depth) {
    if (++depth > keys.length) return map;
    var array, sortKey = sortKeys[depth - 1];
    if (rollup != null && depth >= keys.length) array = map.entries();
    else array = [], map.each(function(v, k) { array.push({key: k, values: entries(v, depth)}); });
    return sortKey != null ? array.sort(function(a, b) { return sortKey(a.key, b.key); }) : array;
  }

  return nest = {
    object: function(array) { return apply(array, 0, createObject, setObject); },
    map: function(array) { return apply(array, 0, createMap, setMap); },
    entries: function(array) { return entries(apply(array, 0, createMap, setMap), 0); },
    key: function(d) { keys.push(d); return nest; },
    sortKeys: function(order) { sortKeys[keys.length - 1] = order; return nest; },
    sortValues: function(order) { sortValues = order; return nest; },
    rollup: function(f) { rollup = f; return nest; }
  };
});

function createObject() {
  return {};
}

function setObject(object, key, value) {
  object[key] = value;
}

function createMap() {
  return src_map();
}

function setMap(map, key, value) {
  map.set(key, value);
}

// CONCATENATED MODULE: ./node_modules/d3-collection/src/set.js


function set_Set() {}

var proto = src_map.prototype;

set_Set.prototype = set_set.prototype = {
  constructor: set_Set,
  has: proto.has,
  add: function(value) {
    value += "";
    this[map_prefix + value] = value;
    return this;
  },
  remove: proto.remove,
  clear: proto.clear,
  values: proto.keys,
  size: proto.size,
  empty: proto.empty,
  each: proto.each
};

function set_set(object, f) {
  var set = new set_Set;

  // Copy constructor.
  if (object instanceof set_Set) object.each(function(value) { set.add(value); });

  // Otherwise, assume it’s an array.
  else if (object) {
    var i = -1, n = object.length;
    if (f == null) while (++i < n) set.add(object[i]);
    else while (++i < n) set.add(f(object[i], i, object));
  }

  return set;
}

/* harmony default export */ var src_set = (set_set);

// CONCATENATED MODULE: ./node_modules/d3-collection/src/keys.js
/* harmony default export */ var src_keys = (function(map) {
  var keys = [];
  for (var key in map) keys.push(key);
  return keys;
});

// CONCATENATED MODULE: ./node_modules/d3-collection/src/values.js
/* harmony default export */ var src_values = (function(map) {
  var values = [];
  for (var key in map) values.push(map[key]);
  return values;
});

// CONCATENATED MODULE: ./node_modules/d3-collection/src/entries.js
/* harmony default export */ var src_entries = (function(map) {
  var entries = [];
  for (var key in map) entries.push({key: key, value: map[key]});
  return entries;
});

// CONCATENATED MODULE: ./node_modules/d3-collection/src/index.js







// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/merge.js



/**
    @function merge
    @desc Combines an Array of Objects together and returns a new Object.
    @param {Array} objects The Array of objects to be merged together.
    @param {Object} aggs An object containing specific aggregation methods (functions) for each key type. By default, numbers are summed and strings are returned as an array of unique values.
    @example <caption>this</caption>
merge([
  {id: "foo", group: "A", value: 10, links: [1, 2]},
  {id: "bar", group: "A", value: 20, links: [1, 3]}
]);
    @example <caption>returns this</caption>
{id: ["bar", "foo"], group: "A", value: 30, links: [1, 2, 3]}
*/
function objectMerge(objects, aggs) {
  if ( aggs === void 0 ) aggs = {};


  var availableKeys = new Set(src_merge(objects.map(function (o) { return src_keys(o); }))),
        newObject = {};

  availableKeys.forEach(function (k) {
    var values = objects.map(function (o) { return o[k]; });
    var value;
    if (aggs[k]) { value = aggs[k](values); }
    else {
      var types = values.map(function (v) { return v || v === false ? v.constructor : v; }).filter(function (v) { return v !== void 0; });
      if (!types.length) { value = undefined; }
      else if (types.indexOf(Array) >= 0) {
        value = src_merge(values.map(function (v) { return v instanceof Array ? v : [v]; }));
        value = Array.from(new Set(value));
        if (value.length === 1) { value = value[0]; }
      }
      else if (types.indexOf(String) >= 0) {
        value = Array.from(new Set(values));
        if (value.length === 1) { value = value[0]; }
      }
      else if (types.indexOf(Number) >= 0) { value = src_sum(values); }
      else if (types.indexOf(Object) >= 0) { value = objectMerge(values.filter(function (v) { return v; })); }
      else {
        value = Array.from(new Set(values.filter(function (v) { return v !== void 0; })));
        if (value.length === 1) { value = value[0]; }
      }
    }
    newObject[k] = value;
  });

  return newObject;

}

/* harmony default export */ var es_src_merge = (objectMerge);

//# sourceMappingURL=merge.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/parseSides.js
/**
 @function parseSides
 @desc Converts a string of directional CSS shorthand values into an object with the values expanded.
 @param {String|Number} sides The CSS shorthand string to expand.
 */
/* harmony default export */ var parseSides = (function(sides) {
  var values;
  if (typeof sides === "number") { values = [sides]; }
  else { values = sides.split(/\s+/); }

  if (values.length === 1) { values = [values[0], values[0], values[0], values[0]]; }
  else if (values.length === 2) { values = values.concat(values); }
  else if (values.length === 3) { values.push(values[1]); }

  return [
    "top",
    "right",
    "bottom",
    "left"
  ].reduce(function (acc, direction, i) {
    var value = parseFloat(values[i]);
    acc[direction] = value || 0;
    return acc;
  }, {});
});

//# sourceMappingURL=parseSides.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/prefix.js
/**
    @function prefix
    @desc Returns the appropriate CSS vendor prefix, given the current browser.
*/
/* harmony default export */ var src_prefix = (function() {
  if ("-webkit-transform" in document.body.style) { return "-webkit-"; }
  else if ("-moz-transform" in document.body.style) { return "-moz-"; }
  else if ("-ms-transform" in document.body.style) { return "-ms-"; }
  else if ("-o-transform" in document.body.style) { return "-o-"; }
  else { return ""; }
});

//# sourceMappingURL=prefix.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/src/stylize.js
/**
    @function stylize
    @desc Applies each key/value in an object as a style.
    @param {D3selection} elem The D3 element to apply the styles to.
    @param {Object} styles An object of key/value style pairs.
*/
/* harmony default export */ var stylize = (function(e, s) {
  if ( s === void 0 ) s = {};

  for (var k in s) { if ({}.hasOwnProperty.call(s, k)) { e.style(k, s[k]); } }
});

//# sourceMappingURL=stylize.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-common/es/index.js
















//# sourceMappingURL=index.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/combiningMarks.js
// scraped from http://www.fileformat.info/info/unicode/category/Mc/list.htm
// and http://www.fileformat.info/info/unicode/category/Mn/list.htm
// JSON.stringify([].slice.call(document.getElementsByClassName("table-list")[0].getElementsByTagName("tr")).filter(function(d){ return d.getElementsByTagName("a").length && d.getElementsByTagName("a")[0].innerHTML.length === 6; }).map(function(d){ return d.getElementsByTagName("a")[0].innerHTML.replace("U", "u").replace("+", ""); }).sort());
// The following unicode characters combine to form new characters and should never be split from surrounding characters.
var combiningMarks_a = ["u0903", "u093B", "u093E", "u093F", "u0940", "u0949", "u094A", "u094B", "u094C", "u094E", "u094F", "u0982", "u0983", "u09BE", "u09BF", "u09C0", "u09C7", "u09C8", "u09CB", "u09CC", "u09D7", "u0A03", "u0A3E", "u0A3F", "u0A40", "u0A83", "u0ABE", "u0ABF", "u0AC0", "u0AC9", "u0ACB", "u0ACC", "u0B02", "u0B03", "u0B3E", "u0B40", "u0B47", "u0B48", "u0B4B", "u0B4C", "u0B57", "u0BBE", "u0BBF", "u0BC1", "u0BC2", "u0BC6", "u0BC7", "u0BC8", "u0BCA", "u0BCB", "u0BCC", "u0BD7", "u0C01", "u0C02", "u0C03", "u0C41", "u0C42", "u0C43", "u0C44", "u0C82", "u0C83", "u0CBE", "u0CC0", "u0CC1", "u0CC2", "u0CC3", "u0CC4", "u0CC7", "u0CC8", "u0CCA", "u0CCB", "u0CD5", "u0CD6", "u0D02", "u0D03", "u0D3E", "u0D3F", "u0D40", "u0D46", "u0D47", "u0D48", "u0D4A", "u0D4B", "u0D4C", "u0D57", "u0D82", "u0D83", "u0DCF", "u0DD0", "u0DD1", "u0DD8", "u0DD9", "u0DDA", "u0DDB", "u0DDC", "u0DDD", "u0DDE", "u0DDF", "u0DF2", "u0DF3", "u0F3E", "u0F3F", "u0F7F", "u102B", "u102C", "u1031", "u1038", "u103B", "u103C", "u1056", "u1057", "u1062", "u1063", "u1064", "u1067", "u1068", "u1069", "u106A", "u106B", "u106C", "u106D", "u1083", "u1084", "u1087", "u1088", "u1089", "u108A", "u108B", "u108C", "u108F", "u109A", "u109B", "u109C", "u17B6", "u17BE", "u17BF", "u17C0", "u17C1", "u17C2", "u17C3", "u17C4", "u17C5", "u17C7", "u17C8", "u1923", "u1924", "u1925", "u1926", "u1929", "u192A", "u192B", "u1930", "u1931", "u1933", "u1934", "u1935", "u1936", "u1937", "u1938", "u1A19", "u1A1A", "u1A55", "u1A57", "u1A61", "u1A63", "u1A64", "u1A6D", "u1A6E", "u1A6F", "u1A70", "u1A71", "u1A72", "u1B04", "u1B35", "u1B3B", "u1B3D", "u1B3E", "u1B3F", "u1B40", "u1B41", "u1B43", "u1B44", "u1B82", "u1BA1", "u1BA6", "u1BA7", "u1BAA", "u1BE7", "u1BEA", "u1BEB", "u1BEC", "u1BEE", "u1BF2", "u1BF3", "u1C24", "u1C25", "u1C26", "u1C27", "u1C28", "u1C29", "u1C2A", "u1C2B", "u1C34", "u1C35", "u1CE1", "u1CF2", "u1CF3", "u302E", "u302F", "uA823", "uA824", "uA827", "uA880", "uA881", "uA8B4", "uA8B5", "uA8B6", "uA8B7", "uA8B8", "uA8B9", "uA8BA", "uA8BB", "uA8BC", "uA8BD", "uA8BE", "uA8BF", "uA8C0", "uA8C1", "uA8C2", "uA8C3", "uA952", "uA953", "uA983", "uA9B4", "uA9B5", "uA9BA", "uA9BB", "uA9BD", "uA9BE", "uA9BF", "uA9C0", "uAA2F", "uAA30", "uAA33", "uAA34", "uAA4D", "uAA7B", "uAA7D", "uAAEB", "uAAEE", "uAAEF", "uAAF5", "uABE3", "uABE4", "uABE6", "uABE7", "uABE9", "uABEA", "uABEC"];
var combiningMarks_b = ["u0300", "u0301", "u0302", "u0303", "u0304", "u0305", "u0306", "u0307", "u0308", "u0309", "u030A", "u030B", "u030C", "u030D", "u030E", "u030F", "u0310", "u0311", "u0312", "u0313", "u0314", "u0315", "u0316", "u0317", "u0318", "u0319", "u031A", "u031B", "u031C", "u031D", "u031E", "u031F", "u0320", "u0321", "u0322", "u0323", "u0324", "u0325", "u0326", "u0327", "u0328", "u0329", "u032A", "u032B", "u032C", "u032D", "u032E", "u032F", "u0330", "u0331", "u0332", "u0333", "u0334", "u0335", "u0336", "u0337", "u0338", "u0339", "u033A", "u033B", "u033C", "u033D", "u033E", "u033F", "u0340", "u0341", "u0342", "u0343", "u0344", "u0345", "u0346", "u0347", "u0348", "u0349", "u034A", "u034B", "u034C", "u034D", "u034E", "u034F", "u0350", "u0351", "u0352", "u0353", "u0354", "u0355", "u0356", "u0357", "u0358", "u0359", "u035A", "u035B", "u035C", "u035D", "u035E", "u035F", "u0360", "u0361", "u0362", "u0363", "u0364", "u0365", "u0366", "u0367", "u0368", "u0369", "u036A", "u036B", "u036C", "u036D", "u036E", "u036F", "u0483", "u0484", "u0485", "u0486", "u0487", "u0591", "u0592", "u0593", "u0594", "u0595", "u0596", "u0597", "u0598", "u0599", "u059A", "u059B", "u059C", "u059D", "u059E", "u059F", "u05A0", "u05A1", "u05A2", "u05A3", "u05A4", "u05A5", "u05A6", "u05A7", "u05A8", "u05A9", "u05AA", "u05AB", "u05AC", "u05AD", "u05AE", "u05AF", "u05B0", "u05B1", "u05B2", "u05B3", "u05B4", "u05B5", "u05B6", "u05B7", "u05B8", "u05B9", "u05BA", "u05BB", "u05BC", "u05BD", "u05BF", "u05C1", "u05C2", "u05C4", "u05C5", "u05C7", "u0610", "u0611", "u0612", "u0613", "u0614", "u0615", "u0616", "u0617", "u0618", "u0619", "u061A", "u064B", "u064C", "u064D", "u064E", "u064F", "u0650", "u0651", "u0652", "u0653", "u0654", "u0655", "u0656", "u0657", "u0658", "u0659", "u065A", "u065B", "u065C", "u065D", "u065E", "u065F", "u0670", "u06D6", "u06D7", "u06D8", "u06D9", "u06DA", "u06DB", "u06DC", "u06DF", "u06E0", "u06E1", "u06E2", "u06E3", "u06E4", "u06E7", "u06E8", "u06EA", "u06EB", "u06EC", "u06ED", "u0711", "u0730", "u0731", "u0732", "u0733", "u0734", "u0735", "u0736", "u0737", "u0738", "u0739", "u073A", "u073B", "u073C", "u073D", "u073E", "u073F", "u0740", "u0741", "u0742", "u0743", "u0744", "u0745", "u0746", "u0747", "u0748", "u0749", "u074A", "u07A6", "u07A7", "u07A8", "u07A9", "u07AA", "u07AB", "u07AC", "u07AD", "u07AE", "u07AF", "u07B0", "u07EB", "u07EC", "u07ED", "u07EE", "u07EF", "u07F0", "u07F1", "u07F2", "u07F3", "u0816", "u0817", "u0818", "u0819", "u081B", "u081C", "u081D", "u081E", "u081F", "u0820", "u0821", "u0822", "u0823", "u0825", "u0826", "u0827", "u0829", "u082A", "u082B", "u082C", "u082D", "u0859", "u085A", "u085B", "u08E3", "u08E4", "u08E5", "u08E6", "u08E7", "u08E8", "u08E9", "u08EA", "u08EB", "u08EC", "u08ED", "u08EE", "u08EF", "u08F0", "u08F1", "u08F2", "u08F3", "u08F4", "u08F5", "u08F6", "u08F7", "u08F8", "u08F9", "u08FA", "u08FB", "u08FC", "u08FD", "u08FE", "u08FF", "u0900", "u0901", "u0902", "u093A", "u093C", "u0941", "u0942", "u0943", "u0944", "u0945", "u0946", "u0947", "u0948", "u094D", "u0951", "u0952", "u0953", "u0954", "u0955", "u0956", "u0957", "u0962", "u0963", "u0981", "u09BC", "u09C1", "u09C2", "u09C3", "u09C4", "u09CD", "u09E2", "u09E3", "u0A01", "u0A02", "u0A3C", "u0A41", "u0A42", "u0A47", "u0A48", "u0A4B", "u0A4C", "u0A4D", "u0A51", "u0A70", "u0A71", "u0A75", "u0A81", "u0A82", "u0ABC", "u0AC1", "u0AC2", "u0AC3", "u0AC4", "u0AC5", "u0AC7", "u0AC8", "u0ACD", "u0AE2", "u0AE3", "u0B01", "u0B3C", "u0B3F", "u0B41", "u0B42", "u0B43", "u0B44", "u0B4D", "u0B56", "u0B62", "u0B63", "u0B82", "u0BC0", "u0BCD", "u0C00", "u0C3E", "u0C3F", "u0C40", "u0C46", "u0C47", "u0C48", "u0C4A", "u0C4B", "u0C4C", "u0C4D", "u0C55", "u0C56", "u0C62", "u0C63", "u0C81", "u0CBC", "u0CBF", "u0CC6", "u0CCC", "u0CCD", "u0CE2", "u0CE3", "u0D01", "u0D41", "u0D42", "u0D43", "u0D44", "u0D4D", "u0D62", "u0D63", "u0DCA", "u0DD2", "u0DD3", "u0DD4", "u0DD6", "u0E31", "u0E34", "u0E35", "u0E36", "u0E37", "u0E38", "u0E39", "u0E3A", "u0E47", "u0E48", "u0E49", "u0E4A", "u0E4B", "u0E4C", "u0E4D", "u0E4E", "u0EB1", "u0EB4", "u0EB5", "u0EB6", "u0EB7", "u0EB8", "u0EB9", "u0EBB", "u0EBC", "u0EC8", "u0EC9", "u0ECA", "u0ECB", "u0ECC", "u0ECD", "u0F18", "u0F19", "u0F35", "u0F37", "u0F39", "u0F71", "u0F72", "u0F73", "u0F74", "u0F75", "u0F76", "u0F77", "u0F78", "u0F79", "u0F7A", "u0F7B", "u0F7C", "u0F7D", "u0F7E", "u0F80", "u0F81", "u0F82", "u0F83", "u0F84", "u0F86", "u0F87", "u0F8D", "u0F8E", "u0F8F", "u0F90", "u0F91", "u0F92", "u0F93", "u0F94", "u0F95", "u0F96", "u0F97", "u0F99", "u0F9A", "u0F9B", "u0F9C", "u0F9D", "u0F9E", "u0F9F", "u0FA0", "u0FA1", "u0FA2", "u0FA3", "u0FA4", "u0FA5", "u0FA6", "u0FA7", "u0FA8", "u0FA9", "u0FAA", "u0FAB", "u0FAC", "u0FAD", "u0FAE", "u0FAF", "u0FB0", "u0FB1", "u0FB2", "u0FB3", "u0FB4", "u0FB5", "u0FB6", "u0FB7", "u0FB8", "u0FB9", "u0FBA", "u0FBB", "u0FBC", "u0FC6", "u102D", "u102E", "u102F", "u1030", "u1032", "u1033", "u1034", "u1035", "u1036", "u1037", "u1039", "u103A", "u103D", "u103E", "u1058", "u1059", "u105E", "u105F", "u1060", "u1071", "u1072", "u1073", "u1074", "u1082", "u1085", "u1086", "u108D", "u109D", "u135D", "u135E", "u135F", "u1712", "u1713", "u1714", "u1732", "u1733", "u1734", "u1752", "u1753", "u1772", "u1773", "u17B4", "u17B5", "u17B7", "u17B8", "u17B9", "u17BA", "u17BB", "u17BC", "u17BD", "u17C6", "u17C9", "u17CA", "u17CB", "u17CC", "u17CD", "u17CE", "u17CF", "u17D0", "u17D1", "u17D2", "u17D3", "u17DD", "u180B", "u180C", "u180D", "u18A9", "u1920", "u1921", "u1922", "u1927", "u1928", "u1932", "u1939", "u193A", "u193B", "u1A17", "u1A18", "u1A1B", "u1A56", "u1A58", "u1A59", "u1A5A", "u1A5B", "u1A5C", "u1A5D", "u1A5E", "u1A60", "u1A62", "u1A65", "u1A66", "u1A67", "u1A68", "u1A69", "u1A6A", "u1A6B", "u1A6C", "u1A73", "u1A74", "u1A75", "u1A76", "u1A77", "u1A78", "u1A79", "u1A7A", "u1A7B", "u1A7C", "u1A7F", "u1AB0", "u1AB1", "u1AB2", "u1AB3", "u1AB4", "u1AB5", "u1AB6", "u1AB7", "u1AB8", "u1AB9", "u1ABA", "u1ABB", "u1ABC", "u1ABD", "u1B00", "u1B01", "u1B02", "u1B03", "u1B34", "u1B36", "u1B37", "u1B38", "u1B39", "u1B3A", "u1B3C", "u1B42", "u1B6B", "u1B6C", "u1B6D", "u1B6E", "u1B6F", "u1B70", "u1B71", "u1B72", "u1B73", "u1B80", "u1B81", "u1BA2", "u1BA3", "u1BA4", "u1BA5", "u1BA8", "u1BA9", "u1BAB", "u1BAC", "u1BAD", "u1BE6", "u1BE8", "u1BE9", "u1BED", "u1BEF", "u1BF0", "u1BF1", "u1C2C", "u1C2D", "u1C2E", "u1C2F", "u1C30", "u1C31", "u1C32", "u1C33", "u1C36", "u1C37", "u1CD0", "u1CD1", "u1CD2", "u1CD4", "u1CD5", "u1CD6", "u1CD7", "u1CD8", "u1CD9", "u1CDA", "u1CDB", "u1CDC", "u1CDD", "u1CDE", "u1CDF", "u1CE0", "u1CE2", "u1CE3", "u1CE4", "u1CE5", "u1CE6", "u1CE7", "u1CE8", "u1CED", "u1CF4", "u1CF8", "u1CF9", "u1DC0", "u1DC1", "u1DC2", "u1DC3", "u1DC4", "u1DC5", "u1DC6", "u1DC7", "u1DC8", "u1DC9", "u1DCA", "u1DCB", "u1DCC", "u1DCD", "u1DCE", "u1DCF", "u1DD0", "u1DD1", "u1DD2", "u1DD3", "u1DD4", "u1DD5", "u1DD6", "u1DD7", "u1DD8", "u1DD9", "u1DDA", "u1DDB", "u1DDC", "u1DDD", "u1DDE", "u1DDF", "u1DE0", "u1DE1", "u1DE2", "u1DE3", "u1DE4", "u1DE5", "u1DE6", "u1DE7", "u1DE8", "u1DE9", "u1DEA", "u1DEB", "u1DEC", "u1DED", "u1DEE", "u1DEF", "u1DF0", "u1DF1", "u1DF2", "u1DF3", "u1DF4", "u1DF5", "u1DFC", "u1DFD", "u1DFE", "u1DFF", "u20D0", "u20D1", "u20D2", "u20D3", "u20D4", "u20D5", "u20D6", "u20D7", "u20D8", "u20D9", "u20DA", "u20DB", "u20DC", "u20E1", "u20E5", "u20E6", "u20E7", "u20E8", "u20E9", "u20EA", "u20EB", "u20EC", "u20ED", "u20EE", "u20EF", "u20F0", "u2CEF", "u2CF0", "u2CF1", "u2D7F", "u2DE0", "u2DE1", "u2DE2", "u2DE3", "u2DE4", "u2DE5", "u2DE6", "u2DE7", "u2DE8", "u2DE9", "u2DEA", "u2DEB", "u2DEC", "u2DED", "u2DEE", "u2DEF", "u2DF0", "u2DF1", "u2DF2", "u2DF3", "u2DF4", "u2DF5", "u2DF6", "u2DF7", "u2DF8", "u2DF9", "u2DFA", "u2DFB", "u2DFC", "u2DFD", "u2DFE", "u2DFF", "u302A", "u302B", "u302C", "u302D", "u3099", "u309A", "uA66F", "uA674", "uA675", "uA676", "uA677", "uA678", "uA679", "uA67A", "uA67B", "uA67C", "uA67D", "uA69E", "uA69F", "uA6F0", "uA6F1", "uA802", "uA806", "uA80B", "uA825", "uA826", "uA8C4", "uA8E0", "uA8E1", "uA8E2", "uA8E3", "uA8E4", "uA8E5", "uA8E6", "uA8E7", "uA8E8", "uA8E9", "uA8EA", "uA8EB", "uA8EC", "uA8ED", "uA8EE", "uA8EF", "uA8F0", "uA8F1", "uA926", "uA927", "uA928", "uA929", "uA92A", "uA92B", "uA92C", "uA92D", "uA947", "uA948", "uA949", "uA94A", "uA94B", "uA94C", "uA94D", "uA94E", "uA94F", "uA950", "uA951", "uA980", "uA981", "uA982", "uA9B3", "uA9B6", "uA9B7", "uA9B8", "uA9B9", "uA9BC", "uA9E5", "uAA29", "uAA2A", "uAA2B", "uAA2C", "uAA2D", "uAA2E", "uAA31", "uAA32", "uAA35", "uAA36", "uAA43", "uAA4C", "uAA7C", "uAAB0", "uAAB2", "uAAB3", "uAAB4", "uAAB7", "uAAB8", "uAABE", "uAABF", "uAAC1", "uAAEC", "uAAED", "uAAF6", "uABE5", "uABE8", "uABED", "uFB1E", "uFE00", "uFE01", "uFE02", "uFE03", "uFE04", "uFE05", "uFE06", "uFE07", "uFE08", "uFE09", "uFE0A", "uFE0B", "uFE0C", "uFE0D", "uFE0E", "uFE0F", "uFE20", "uFE21", "uFE22", "uFE23", "uFE24", "uFE25", "uFE26", "uFE27", "uFE28", "uFE29", "uFE2A", "uFE2B", "uFE2C", "uFE2D", "uFE2E", "uFE2F"];
/* harmony default export */ var combiningMarks = (combiningMarks_a.concat(combiningMarks_b));

//# sourceMappingURL=combiningMarks.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/textSplit.js




var splitChars = ["-",  "/",  ";",  ":",  "&",
  "u0E2F",  // thai character pairannoi
  "u0EAF",  // lao ellipsis
  "u0EC6",  // lao ko la (word repetition)
  "u0ECC",  // lao cancellation mark
  "u104A",  // myanmar sign little section
  "u104B",  // myanmar sign section
  "u104C",  // myanmar symbol locative
  "u104D",  // myanmar symbol completed
  "u104E",  // myanmar symbol aforementioned
  "u104F",  // myanmar symbol genitive
  "u2013",  // en dash
  "u2014",  // em dash
  "u2027",  // simplified chinese hyphenation point
  "u3000",  // simplified chinese ideographic space
  "u3001",  // simplified chinese ideographic comma
  "u3002",  // simplified chinese ideographic full stop
  "uFF0C",  // full-width comma
  "uFF5E"   // wave dash
];

var prefixChars = ["'",  "<",  "(",  "{",  "[",
  "u00AB",  // left-pointing double angle quotation mark
  "u300A",  // left double angle bracket
  "u3008"  // left angle bracket
];

var suffixChars = ["'",  ">",  ")",  "}",  "]",  ".",  "!",  "?",
  "u00BB",  // right-pointing double angle quotation mark
  "u300B",  // right double angle bracket
  "u3009"  // right angle bracket
].concat(splitChars);

var burmeseRange = "\u1000-\u102A\u103F-\u1049\u1050-\u1055";
var japaneseRange = "\u3040-\u309f\u30a0-\u30ff\uff00-\uff0b\uff0d-\uff5d\uff5f-\uff9f\u3400-\u4dbf";
var chineseRange = "\u3400-\u9FBF";
var laoRange = "\u0E81-\u0EAE\u0EB0-\u0EC4\u0EC8-\u0ECB\u0ECD-\u0EDD";

var noSpaceRange = burmeseRange + chineseRange + japaneseRange + laoRange;

var splitWords = new RegExp(("(\\" + (splitChars.join("|\\")) + ")*[^\\s|\\" + (splitChars.join("|\\")) + "]*(\\" + (splitChars.join("|\\")) + ")*"), "g");
var noSpaceLanguage = new RegExp(("[" + noSpaceRange + "]"));
var splitAllChars = new RegExp(("(\\" + (prefixChars.join("|\\")) + ")*[" + noSpaceRange + "](\\" + (suffixChars.join("|\\")) + "|\\" + (combiningMarks.join("|\\")) + ")*|[a-z0-9]+"), "gi");

/**
    @function textSplit
    @desc Splits a given sentence into an array of words.
    @param {String} sentence
*/
/* harmony default export */ var textSplit = (function(sentence) {
  if (!noSpaceLanguage.test(sentence)) { return stringify(sentence).match(splitWords).filter(function (w) { return w.length; }); }
  return src_merge(stringify(sentence).match(splitWords).map(function (d) {
    if (noSpaceLanguage.test(d)) { return d.match(splitAllChars); }
    return [d];
  }));
});



//# sourceMappingURL=textSplit.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/textWrap.js





/**
    @function textWrap
    @desc Based on the defined styles and dimensions, breaks a string into an array of strings for each line of text.
*/
/* harmony default export */ var src_textWrap = (function() {

  var fontFamily = "sans-serif",
      fontSize = 10,
      fontWeight = 400,
      height = 200,
      lineHeight,
      maxLines = null,
      overflow = false,
      split = textSplit,
      width = 200;

  /**
      The inner return object and wraps the text and returns the line data array.
      @private
  */
  function textWrap(sentence) {

    sentence = stringify(sentence);

    if (lineHeight === void 0) { lineHeight = Math.ceil(fontSize * 1.4); }

    var words = split(sentence);

    var style = {
      "font-family": fontFamily,
      "font-size": fontSize,
      "font-weight": fontWeight,
      "line-height": lineHeight
    };

    var line = 1,
        textProg = "",
        truncated = false,
        widthProg = 0;

    var lineData = [],
          sizes = textWidth(words, style),
          space = textWidth(" ", style);

    for (var i = 0; i < words.length; i++) {
      var word = words[i];
      var wordWidth = sizes[words.indexOf(word)];
      word += sentence.slice(textProg.length + word.length).match("^( |\n)*", "g")[0];
      if (textProg.slice(-1) === "\n" || widthProg + wordWidth > width) {
        if (!i && !overflow) {
          truncated = true;
          break;
        }
        lineData[line - 1] = trimRight(lineData[line - 1]);
        line++;
        if (lineHeight * line > height || wordWidth > width && !overflow || maxLines && line > maxLines) {
          truncated = true;
          break;
        }
        widthProg = 0;
        lineData.push(word);
      }
      else if (!i) { lineData[0] = word; }
      else { lineData[line - 1] += word; }
      textProg += word;
      widthProg += wordWidth;
      widthProg += word.match(/[\s]*$/g)[0].length * space;
    }

    return {
      lines: lineData,
      sentence: sentence, truncated: truncated,
      widths: textWidth(lineData, style),
      words: words
    };

  }

  /**
      @memberof textWrap
      @desc If *value* is specified, sets the font family accessor to the specified function or string and returns this generator. If *value* is not specified, returns the current font family.
      @param {Function|String} [*value* = "sans-serif"]
  */
  textWrap.fontFamily = function(_) {
    return arguments.length ? (fontFamily = _, textWrap) : fontFamily;
  };

  /**
      @memberof textWrap
      @desc If *value* is specified, sets the font size accessor to the specified function or number and returns this generator. If *value* is not specified, returns the current font size.
      @param {Function|Number} [*value* = 10]
  */
  textWrap.fontSize = function(_) {
    return arguments.length ? (fontSize = _, textWrap) : fontSize;
  };

  /**
      @memberof textWrap
      @desc If *value* is specified, sets the font weight accessor to the specified function or number and returns this generator. If *value* is not specified, returns the current font weight.
      @param {Function|Number|String} [*value* = 400]
  */
  textWrap.fontWeight = function(_) {
    return arguments.length ? (fontWeight = _, textWrap) : fontWeight;
  };

  /**
      @memberof textWrap
      @desc If *value* is specified, sets height limit to the specified value and returns this generator. If *value* is not specified, returns the current value.
      @param {Number} [*value* = 200]
  */
  textWrap.height = function(_) {
    return arguments.length ? (height = _, textWrap) : height;
  };

  /**
      @memberof textWrap
      @desc If *value* is specified, sets the line height accessor to the specified function or number and returns this generator. If *value* is not specified, returns the current line height accessor, which is 1.1 times the [font size](#textWrap.fontSize) by default.
      @param {Function|Number} [*value*]
  */
  textWrap.lineHeight = function(_) {
    return arguments.length ? (lineHeight = _, textWrap) : lineHeight;
  };

  /**
      @memberof textWrap
      @desc If *value* is specified, sets the maximum number of lines allowed when wrapping.
      @param {Function|Number} [*value*]
  */
  textWrap.maxLines = function(_) {
    return arguments.length ? (maxLines = _, textWrap) : maxLines;
  };

  /**
      @memberof textWrap
      @desc If *value* is specified, sets the overflow to the specified boolean and returns this generator. If *value* is not specified, returns the current overflow value.
      @param {Boolean} [*value* = false]
  */
  textWrap.overflow = function(_) {
    return arguments.length ? (overflow = _, textWrap) : overflow;
  };

  /**
      @memberof textWrap
      @desc If *value* is specified, sets the word split function to the specified function and returns this generator. If *value* is not specified, returns the current word split function.
      @param {Function} [*value*] A function that, when passed a string, is expected to return that string split into an array of words to textWrap. The default split function splits strings on the following characters: `-`, `/`, `;`, `:`, `&`
  */
  textWrap.split = function(_) {
    return arguments.length ? (split = _, textWrap) : split;
  };

  /**
      @memberof textWrap
      @desc If *value* is specified, sets width limit to the specified value and returns this generator. If *value* is not specified, returns the current value.
      @param {Number} [*value* = 200]
  */
  textWrap.width = function(_) {
    return arguments.length ? (width = _, textWrap) : width;
  };

  return textWrap;

});

//# sourceMappingURL=textWrap.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/TextBox.js
/**
    @external BaseClass
    @see https://github.com/d3plus/d3plus-common#BaseClass
*/















/**
    @class TextBox
    @extends external:BaseClass
    @desc Creates a wrapped text box for each point in an array of data. See [this example](https://d3plus.org/examples/d3plus-text/getting-started/) for help getting started using the TextBox class.
*/
var TextBox_TextBox = (function (BaseClass) {
  function TextBox() {
    var this$1 = this;


    BaseClass.call(this);

    this._ariaHidden = es_src_constant("false");
    this._delay = 0;
    this._duration = 0;
    this._ellipsis = function (text, line) { return line ? ((text.replace(/\.|,$/g, "")) + "...") : ""; };
    this._fontColor = es_src_constant("black");
    this._fontFamily = es_src_constant(["Roboto", "Helvetica Neue", "HelveticaNeue", "Helvetica", "Arial", "sans-serif"]);
    this._fontMax = es_src_constant(50);
    this._fontMin = es_src_constant(8);
    this._fontOpacity = es_src_constant(1);
    this._fontResize = es_src_constant(false);
    this._fontSize = es_src_constant(10);
    this._fontWeight = es_src_constant(400);
    this._height = accessor("height", 200);
    this._id = function (d, i) { return d.id || ("" + i); };
    this._lineHeight = function (d, i) { return this$1._fontSize(d, i) * 1.2; };
    this._maxLines = es_src_constant(null);
    this._on = {};
    this._overflow = es_src_constant(false);
    this._padding = es_src_constant(0);
    this._pointerEvents = es_src_constant("auto");
    this._rotate = es_src_constant(0);
    this._rotateAnchor = function (d) { return [d.w / 2, d.h / 2]; };
    this._split = textSplit;
    this._text = accessor("text");
    this._textAnchor = es_src_constant("start");
    this._verticalAlign = es_src_constant("top");
    this._width = accessor("width", 200);
    this._x = accessor("x", 0);
    this._y = accessor("y", 0);

  }

  if ( BaseClass ) TextBox.__proto__ = BaseClass;
  TextBox.prototype = Object.create( BaseClass && BaseClass.prototype );
  TextBox.prototype.constructor = TextBox;

  /**
      @memberof TextBox
      @desc Renders the text boxes. If a *callback* is specified, it will be called once the shapes are done drawing.
      @param {Function} [*callback* = undefined]
  */
  TextBox.prototype.render = function render (callback) {
    var this$1 = this;


    if (this._select === void 0) { this.select(src_select("body").append("svg").style("width", ((window.innerWidth) + "px")).style("height", ((window.innerHeight) + "px")).node()); }

    var that = this;

    var boxes = this._select.selectAll(".d3plus-textBox").data(this._data.reduce(function (arr, d, i) {

      var t = this$1._text(d, i);
      if (t === void 0) { return arr; }

      var resize = this$1._fontResize(d, i);
      var lHRatio = this$1._lineHeight(d, i) / this$1._fontSize(d, i);

      var fS = resize ? this$1._fontMax(d, i) : this$1._fontSize(d, i),
          lH = resize ? fS * lHRatio : this$1._lineHeight(d, i),
          line = 1,
          lineData = [],
          sizes,
          wrapResults;

      var style = {
        "font-family": src_fontExists(this$1._fontFamily(d, i)),
        "font-size": fS,
        "font-weight": this$1._fontWeight(d, i),
        "line-height": lH
      };

      var padding = parseSides(this$1._padding(d, i));

      var h = this$1._height(d, i) - (padding.top + padding.bottom),
            w = this$1._width(d, i) - (padding.left + padding.right);

      var wrapper = src_textWrap()
        .fontFamily(style["font-family"])
        .fontSize(fS)
        .fontWeight(style["font-weight"])
        .lineHeight(lH)
        .maxLines(this$1._maxLines(d, i))
        .height(h)
        .overflow(this$1._overflow(d, i))
        .width(w);

      var fMax = this$1._fontMax(d, i),
            fMin = this$1._fontMin(d, i),
            vA = this$1._verticalAlign(d, i),
            words = this$1._split(t, i);

      /**
          Figures out the lineData to be used for wrapping.
          @private
      */
      function checkSize() {
        var truncate = function () {
          if (line < 1) { lineData = [that._ellipsis("", line)]; }
          else { lineData[line - 1] = that._ellipsis(lineData[line - 1], line); }
        };

        // Constraint the font size
        fS = src_max([fS, fMin]);
        fS = src_min([fS, fMax]);

        if (resize) {
          lH = fS * lHRatio;
          wrapper
            .fontSize(fS)
            .lineHeight(lH);
          style["font-size"] = fS;
          style["line-height"] = lH;
        }

        wrapResults = wrapper(t);
        lineData = wrapResults.lines.filter(function (l) { return l !== ""; });
        line = lineData.length;

        if (wrapResults.truncated) {
          if (resize) {
            fS--;
            if (fS < fMin) {
              fS = fMin;
              truncate();
              return;
            }
            else { checkSize(); }
          }
          else { truncate(); }
        }
      }

      if (w > fMin && (h > lH || resize && h > fMin * lHRatio)) {

        if (resize) {

          sizes = textWidth(words, style);

          var areaMod = 1.165 + w / h * 0.1,
                boxArea = w * h,
                maxWidth = src_max(sizes),
                textArea = src_sum(sizes, function (d) { return d * lH; }) * areaMod;

          if (maxWidth > w || textArea > boxArea) {
            var areaRatio = Math.sqrt(boxArea / textArea),
                  widthRatio = w / maxWidth;
            var sizeRatio = src_min([areaRatio, widthRatio]);
            fS = Math.floor(fS * sizeRatio);
          }

          var heightMax = Math.floor(h * 0.8);
          if (fS > heightMax) { fS = heightMax; }

        }

        checkSize();

      }

      if (lineData.length) {

        var tH = line * lH;
        var r = this$1._rotate(d, i);
        var yP = r === 0 ? vA === "top" ? 0 : vA === "middle" ? h / 2 - tH / 2 : h - tH : 0;
        yP -= lH * 0.1;

        arr.push({
          aH: this$1._ariaHidden(d, i),
          data: d,
          i: i,
          lines: lineData,
          fC: this$1._fontColor(d, i),
          fF: style["font-family"],
          fO: this$1._fontOpacity(d, i),
          fW: style["font-weight"],
          id: this$1._id(d, i),
          tA: this$1._textAnchor(d, i),
          vA: this$1._verticalAlign(d, i),
          widths: wrapResults.widths,
          fS: fS, lH: lH, w: w, h: h, r: r,
          x: this$1._x(d, i) + padding.left,
          y: this$1._y(d, i) + yP + padding.top
        });

      }

      return arr;

    }, []), function (d) { return this$1._id(d.data, d.i); });

    var t = src_transition_transition().duration(this._duration);

    if (this._duration === 0) {

      boxes.exit().remove();

    }
    else {

      boxes.exit().transition().delay(this._duration).remove();

      boxes.exit().selectAll("text").transition(t)
        .attr("opacity", 0)
        .style("opacity", 0);

    }

    function rotate(text) {
      text.attr("transform", function (d, i) {
        var rotateAnchor = that._rotateAnchor(d, i);
        return ("translate(" + (d.x) + ", " + (d.y) + ") rotate(" + (d.r) + ", " + (rotateAnchor[0]) + ", " + (rotateAnchor[1]) + ")");
      });
    }

    var update = boxes.enter().append("g")
        .attr("class", "d3plus-textBox")
        .attr("id", function (d) { return ("d3plus-textBox-" + (strip(d.id))); })
        .call(rotate)
      .merge(boxes);

    var rtl = src_rtl();

    update
      .style("pointer-events", function (d) { return this$1._pointerEvents(d.data, d.i); })
      .each(function(d) {

        /**
            Styles to apply to each <text> element.
            @private
        */
        function textStyle(text) {

          text
            .text(function (t) { return trimRight(t); })
            .attr("aria-hidden", d.aH)
            .attr("dir", rtl ? "rtl" : "ltr")
            .attr("fill", d.fC)
            .attr("text-anchor", d.tA)
            .attr("font-family", d.fF)
            .style("font-family", d.fF)
            .attr("font-size", ((d.fS) + "px"))
            .style("font-size", ((d.fS) + "px"))
            .attr("font-weight", d.fW)
            .style("font-weight", d.fW)
            .attr("x", ((d.tA === "middle" ? d.w / 2 : rtl ? d.tA === "start" ? d.w : 0 : d.tA === "end" ? d.w : 2 * Math.sin(Math.PI * d.r / 180)) + "px"))
            .attr("y", function (t, i) { return d.r === 0 || d.vA === "top" ? (((i + 1) * d.lH - (d.lH - d.fS)) + "px") :
              d.vA === "middle" ?
                (((d.h + d.fS) / 2 - (d.lH - d.fS) + (i - d.lines.length / 2 + 0.5) * d.lH) + "px") :
                ((d.h - 2 * (d.lH - d.fS) - (d.lines.length - (i + 1)) * d.lH + 2 * Math.cos(Math.PI * d.r / 180)) + "px"); });

        }

        var texts = src_select(this).selectAll("text").data(d.lines);

        if (that._duration === 0) {

          texts.call(textStyle);

          texts.exit().remove();

          texts.enter().append("text")
            .attr("dominant-baseline", "alphabetic")
            .style("baseline-shift", "0%")
            .attr("unicode-bidi", "bidi-override")
            .call(textStyle)
            .attr("opacity", d.fO)
            .style("opacity", d.fO);

        }
        else {

          texts.transition(t).call(textStyle);

          texts.exit().transition(t)
            .attr("opacity", 0).remove();

          texts.enter().append("text")
              .attr("dominant-baseline", "alphabetic")
              .style("baseline-shift", "0%")
              .attr("opacity", 0)
              .style("opacity", 0)
              .call(textStyle)
            .merge(texts).transition(t).delay(that._delay)
              .call(textStyle)
              .attr("opacity", d.fO)
              .style("opacity", d.fO);
        }

      })
      .transition(t).call(rotate);

    var events = Object.keys(this._on),
          on = events.reduce(function (obj, e) {
            obj[e] = function (d, i) { return this$1._on[e](d.data, i); };
            return obj;
          }, {});
    for (var e = 0; e < events.length; e++) { update.on(events[e], on[events[e]]); }

    if (callback) { setTimeout(callback, this._duration + 100); }

    return this;

  };

  /**
      @memberof TextBox
      @desc If *value* is specified, sets the aria-hidden attribute to the specified function or string and returns the current class instance.
      @param {Function|String} *value*
      @chainable
  */
  TextBox.prototype.ariaHidden = function ariaHidden (_) {
    return _ !== undefined
      ? (this._ariaHidden = typeof _ === "function" ? _ : es_src_constant(_), this)
      : this._ariaHidden;
  };

  /**
      @memberof TextBox
      @desc Sets the data array to the specified array. A text box will be drawn for each object in the array.
      @param {Array} [*data* = []]
      @chainable
  */
  TextBox.prototype.data = function data (_) {
    return arguments.length ? (this._data = _, this) : this._data;
  };

  /**
      @memberof TextBox
      @desc Sets the animation delay to the specified number in milliseconds.
      @param {Number} [*value* = 0]
      @chainable
  */
  TextBox.prototype.delay = function delay (_) {
    return arguments.length ? (this._delay = _, this) : this._delay;
  };

  /**
      @memberof TextBox
      @desc Sets the animation duration to the specified number in milliseconds.
      @param {Number} [*value* = 0]
      @chainable
  */
  TextBox.prototype.duration = function duration (_) {
    return arguments.length ? (this._duration = _, this) : this._duration;
  };

  /**
      @memberof TextBox
      @desc Sets the function that handles what to do when a line is truncated. It should return the new value for the line, and is passed 2 arguments: the String of text for the line in question, and the number of the line. By default, an ellipsis is added to the end of any line except if it is the first word that cannot fit (in that case, an empty string is returned).
      @param {Function|String} [*value*]
      @chainable
      @example <caption>default accessor</caption>
function(text, line) {
  return line ? text.replace(/\.|,$/g, "") + "..." : "";
}
  */
  TextBox.prototype.ellipsis = function ellipsis (_) {
    return arguments.length ? (this._ellipsis = typeof _ === "function" ? _ : es_src_constant(_), this) : this._ellipsis;
  };

  /**
      @memberof TextBox
      @desc Sets the font color to the specified accessor function or static string, which is inferred from the [DOM selection](#textBox.select) by default.
      @param {Function|String} [*value* = "black"]
      @chainable
  */
  TextBox.prototype.fontColor = function fontColor (_) {
    return arguments.length ? (this._fontColor = typeof _ === "function" ? _ : es_src_constant(_), this) : this._fontColor;
  };

  /**
      @memberof TextBox
      @desc Defines the font-family to be used. The value passed can be either a *String* name of a font, a comma-separated list of font-family fallbacks, an *Array* of fallbacks, or a *Function* that returns either a *String* or an *Array*. If supplying multiple fallback fonts, the [fontExists](#fontExists) function will be used to determine the first available font on the client's machine.
      @param {Array|Function|String} [*value* = ["Roboto", "Helvetica Neue", "HelveticaNeue", "Helvetica", "Arial", "sans-serif"]]
      @chainable
  */
  TextBox.prototype.fontFamily = function fontFamily (_) {
    return arguments.length ? (this._fontFamily = typeof _ === "function" ? _ : es_src_constant(_), this) : this._fontFamily;
  };

  /**
      @memberof TextBox
      @desc Sets the maximum font size to the specified accessor function or static number (which corresponds to pixel units), which is used when [dynamically resizing fonts](#textBox.fontResize).
      @param {Function|Number} [*value* = 50]
      @chainable
  */
  TextBox.prototype.fontMax = function fontMax (_) {
    return arguments.length ? (this._fontMax = typeof _ === "function" ? _ : es_src_constant(_), this) : this._fontMax;
  };

  /**
      @memberof TextBox
      @desc Sets the minimum font size to the specified accessor function or static number (which corresponds to pixel units), which is used when [dynamically resizing fonts](#textBox.fontResize).
      @param {Function|Number} [*value* = 8]
      @chainable
  */
  TextBox.prototype.fontMin = function fontMin (_) {
    return arguments.length ? (this._fontMin = typeof _ === "function" ? _ : es_src_constant(_), this) : this._fontMin;
  };

  /**
      @memberof TextBox
      @desc Sets the font opacity to the specified accessor function or static number between 0 and 1.
      @param {Function|Number} [*value* = 1]
      @chainable
   */
  TextBox.prototype.fontOpacity = function fontOpacity (_) {
    return arguments.length ? (this._fontOpacity = typeof _ === "function" ? _ : es_src_constant(_), this) : this._fontOpacity;
  };

  /**
      @memberof TextBox
      @desc Toggles font resizing, which can either be defined as a static boolean for all data points, or an accessor function that returns a boolean. See [this example](http://d3plus.org/examples/d3plus-text/resizing-text/) for a side-by-side comparison.
      @param {Function|Boolean} [*value* = false]
      @chainable
  */
  TextBox.prototype.fontResize = function fontResize (_) {
    return arguments.length ? (this._fontResize = typeof _ === "function" ? _ : es_src_constant(_), this) : this._fontResize;
  };

  /**
      @memberof TextBox
      @desc Sets the font size to the specified accessor function or static number (which corresponds to pixel units), which is inferred from the [DOM selection](#textBox.select) by default.
      @param {Function|Number} [*value* = 10]
      @chainable
  */
  TextBox.prototype.fontSize = function fontSize (_) {
    return arguments.length ? (this._fontSize = typeof _ === "function" ? _ : es_src_constant(_), this) : this._fontSize;
  };

  /**
      @memberof TextBox
      @desc Sets the font weight to the specified accessor function or static number, which is inferred from the [DOM selection](#textBox.select) by default.
      @param {Function|Number|String} [*value* = 400]
      @chainable
  */
  TextBox.prototype.fontWeight = function fontWeight (_) {
    return arguments.length ? (this._fontWeight = typeof _ === "function" ? _ : es_src_constant(_), this) : this._fontWeight;
  };

  /**
      @memberof TextBox
      @desc Sets the height for each box to the specified accessor function or static number.
      @param {Function|Number} [*value*]
      @chainable
      @example <caption>default accessor</caption>
function(d) {
  return d.height || 200;
}
  */
  TextBox.prototype.height = function height (_) {
    return arguments.length ? (this._height = typeof _ === "function" ? _ : es_src_constant(_), this) : this._height;
  };

  /**
      @memberof TextBox
      @desc Defines the unique id for each box to the specified accessor function or static number.
      @param {Function|Number} [*value*]
      @chainable
      @example <caption>default accessor</caption>
function(d, i) {
  return d.id || i + "";
}
  */
  TextBox.prototype.id = function id (_) {
    return arguments.length ? (this._id = typeof _ === "function" ? _ : es_src_constant(_), this) : this._id;
  };

  /**
      @memberof TextBox
      @desc Sets the line height to the specified accessor function or static number, which is 1.2 times the [font size](#textBox.fontSize) by default.
      @param {Function|Number} [*value*]
      @chainable
  */
  TextBox.prototype.lineHeight = function lineHeight (_) {
    return arguments.length ? (this._lineHeight = typeof _ === "function" ? _ : es_src_constant(_), this) : this._lineHeight;
  };

  /**
      @memberof TextBox
      @desc Restricts the maximum number of lines to wrap onto, which is null (unlimited) by default.
      @param {Function|Number} [*value*]
      @chainable
  */
  TextBox.prototype.maxLines = function maxLines (_) {
    return arguments.length ? (this._maxLines = typeof _ === "function" ? _ : es_src_constant(_), this) : this._maxLines;
  };

  /**
      @memberof TextBox
      @desc Sets the text overflow to the specified accessor function or static boolean.
      @param {Function|Boolean} [*value* = false]
      @chainable
  */
  TextBox.prototype.overflow = function overflow (_) {
    return arguments.length ? (this._overflow = typeof _ === "function" ? _ : es_src_constant(_), this) : this._overflow;
  };

  /**
      @memberof TextBox
      @desc Sets the padding to the specified accessor function, CSS shorthand string, or static number, which is 0 by default.
      @param {Function|Number|String} [*value*]
      @chainable
  */
  TextBox.prototype.padding = function padding (_) {
    return arguments.length ? (this._padding = typeof _ === "function" ? _ : es_src_constant(_), this) : this._padding;
  };

  /**
      @memberof TextBox
      @desc Sets the pointer-events to the specified accessor function or static string.
      @param {Function|String} [*value* = "auto"]
      @chainable
  */
  TextBox.prototype.pointerEvents = function pointerEvents (_) {
    return arguments.length ? (this._pointerEvents = typeof _ === "function" ? _ : es_src_constant(_), this) : this._pointerEvents;
  };

  /**
      @memberof TextBox
      @desc Sets the rotate percentage for each box to the specified accessor function or static string.
      @param {Function|Number} [*value* = 0]
      @chainable
  */
  TextBox.prototype.rotate = function rotate (_) {
    return arguments.length ? (this._rotate = typeof _ === "function" ? _ : es_src_constant(_), this) : this._rotate;
  };

  /**
      @memberof TextBox
      @desc Sets the anchor point around which to rotate the text box.
      @param {Function|Number[]}
      @chainable
   */
  TextBox.prototype.rotateAnchor = function rotateAnchor (_) {
    return arguments.length ? (this._rotateAnchor = typeof _ === "function" ? _ : es_src_constant(_), this) : this._rotateAnchor;
  };

  /**
      @memberof TextBox
      @desc Sets the SVG container element to the specified d3 selector or DOM element. If not explicitly specified, an SVG element will be added to the page for use.
      @param {String|HTMLElement} [*selector*]
      @chainable
  */
  TextBox.prototype.select = function select$1 (_) {
    return arguments.length ? (this._select = src_select(_), this) : this._select;
  };

  /**
      @memberof TextBox
      @desc Sets the word split behavior to the specified function, which when passed a string is expected to return that string split into an array of words.
      @param {Function} [*value*]
      @chainable
  */
  TextBox.prototype.split = function split (_) {
    return arguments.length ? (this._split = _, this) : this._split;
  };

  /**
      @memberof TextBox
      @desc Sets the text for each box to the specified accessor function or static string.
      @param {Function|String} [*value*]
      @chainable
      @example <caption>default accessor</caption>
function(d) {
  return d.text;
}
  */
  TextBox.prototype.text = function text (_) {
    return arguments.length ? (this._text = typeof _ === "function" ? _ : es_src_constant(_), this) : this._text;
  };

  /**
      @memberof TextBox
      @desc Sets the horizontal text anchor to the specified accessor function or static string, whose values are analagous to the SVG [text-anchor](https://developer.mozilla.org/en-US/docs/Web/SVG/Attribute/text-anchor) property.
      @param {Function|String} [*value* = "start"]
      @chainable
  */
  TextBox.prototype.textAnchor = function textAnchor (_) {
    return arguments.length ? (this._textAnchor = typeof _ === "function" ? _ : es_src_constant(_), this) : this._textAnchor;
  };

  /**
      @memberof TextBox
      @desc Sets the vertical alignment to the specified accessor function or static string. Accepts `"top"`, `"middle"`, and `"bottom"`.
      @param {Function|String} [*value* = "top"]
      @chainable
  */
  TextBox.prototype.verticalAlign = function verticalAlign (_) {
    return arguments.length ? (this._verticalAlign = typeof _ === "function" ? _ : es_src_constant(_), this) : this._verticalAlign;
  };

  /**
      @memberof TextBox
      @desc Sets the width for each box to the specified accessor function or static number.
      @param {Function|Number} [*value*]
      @chainable
      @example <caption>default accessor</caption>
function(d) {
  return d.width || 200;
}
  */
  TextBox.prototype.width = function width (_) {
    return arguments.length ? (this._width = typeof _ === "function" ? _ : es_src_constant(_), this) : this._width;
  };

  /**
      @memberof TextBox
      @desc Sets the x position for each box to the specified accessor function or static number. The number given should correspond to the left side of the textBox.
      @param {Function|Number} [*value*]
      @chainable
      @example <caption>default accessor</caption>
function(d) {
  return d.x || 0;
}
  */
  TextBox.prototype.x = function x (_) {
    return arguments.length ? (this._x = typeof _ === "function" ? _ : es_src_constant(_), this) : this._x;
  };

  /**
      @memberof TextBox
      @desc Sets the y position for each box to the specified accessor function or static number. The number given should correspond to the top side of the textBox.
      @param {Function|Number} [*value*]
      @chainable
      @example <caption>default accessor</caption>
function(d) {
  return d.y || 0;
}
  */
  TextBox.prototype.y = function y (_) {
    return arguments.length ? (this._y = typeof _ === "function" ? _ : es_src_constant(_), this) : this._y;
  };

  return TextBox;
}(src_BaseClass));

/* harmony default export */ var src_TextBox = (TextBox_TextBox);

//# sourceMappingURL=TextBox.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/src/titleCase.js


var lowercase = ["a", "an", "and", "as", "at", "but", "by", "for", "from", "if", "in", "into", "near", "nor", "of", "on", "onto", "or", "per", "that", "the", "to", "with", "via", "vs", "vs."];
var uppercase = ["CEO", "CFO", "CNC", "COO", "CPU", "GDP", "HVAC", "ID", "IT", "R&D", "TV", "UI"];

/**
    @function titleCase
    @desc Capitalizes the first letter of each word in a phrase/sentence.
    @param {String} str The string to apply the title case logic.
*/
/* harmony default export */ var titleCase = (function(str) {

  if (str === void 0) { return ""; }

  var smalls = lowercase.map(function (s) { return s.toLowerCase(); });

  var bigs = uppercase.slice();
  bigs = bigs.concat(bigs.map(function (b) { return (b + "s"); }));
  var biglow = bigs.map(function (b) { return b.toLowerCase(); });

  var split = textSplit(str);
  return split.map(function (s, i) {
    if (s) {
      var lower = s.toLowerCase();
      var stripped = suffixChars.includes(lower.charAt(lower.length - 1)) ? lower.slice(0, -1) : lower;
      var bigindex = biglow.indexOf(stripped);
      if (bigindex >= 0) { return bigs[bigindex]; }
      else if (smalls.includes(stripped) && i !== 0 && i !== split.length - 1) { return lower; }
      else { return s.charAt(0).toUpperCase() + s.substr(1).toLowerCase(); }
    }
    else { return ""; }
  }).reduce(function (ret, s, i) {
    if (i && str.charAt(ret.length) === " ") { ret += " "; }
    ret += s;
    return ret;
  }, "");

});

//# sourceMappingURL=titleCase.js.map
// CONCATENATED MODULE: ./node_modules/d3plus-text/es/index.js











//# sourceMappingURL=index.js.map
// CONCATENATED MODULE: ./src/js/NodeSettings.js
function NodeSettings_objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; var ownKeys = Object.keys(source); if (typeof Object.getOwnPropertySymbols === 'function') { ownKeys = ownKeys.concat(Object.getOwnPropertySymbols(source).filter(function (sym) { return Object.getOwnPropertyDescriptor(source, sym).enumerable; })); } ownKeys.forEach(function (key) { NodeSettings_defineProperty(target, key, source[key]); }); } return target; }

function NodeSettings_defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function _classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function _defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function _createClass(Constructor, protoProps, staticProps) { if (protoProps) _defineProperties(Constructor.prototype, protoProps); if (staticProps) _defineProperties(Constructor, staticProps); return Constructor; }

var NodeSettings =
/*#__PURE__*/
function () {
  /**
   * @param {object} ownerObject The owner object
   * @param {object} options The options for the node settings.
   * @param {('nodeSize'|'size')} [options.sizingMode=size] The sizing mode. Should be either 'nodeSize' to automatically size the SVG based on the nodes, or 'size' to use the configured width and height.
   * @param {number} [options.horizontalSpacing=25] The horizontal spacing value.
   * @param {number} [options.verticalSpacing=25] The vertical spacing value.
   */
  function NodeSettings(ownerObject, options) {
    _classCallCheck(this, NodeSettings);

    var mergedOptions = NodeSettings_objectSpread({}, NodeSettings.defaults, options);

    this._ownerObject = ownerObject;
    this._sizingMode = mergedOptions.sizingMode;
    this._horizontalSpacing = mergedOptions.horizontalSpacing;
    this._verticalSpacing = mergedOptions.verticalSpacing;
  }
  /**
   * Gets the owner object.
   *
   * @returns {object} The owner object.
   */


  _createClass(NodeSettings, [{
    key: "back",
    value: function back() {
      return this._ownerObject;
    }
    /**
     * Gets the horizontal spacing value.
     *
     * @returns {number} The horizontal spacing value.
     */

  }, {
    key: "getHorizontalSpacing",
    value: function getHorizontalSpacing() {
      return this._horizontalSpacing;
    }
    /**
     * Sets the horizontal spacing value.
     *
     * @param {number} newHorizontalSpacing The new horizontal spacing value.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setHorizontalSpacing",
    value: function setHorizontalSpacing(newHorizontalSpacing) {
      this._horizontalSpacing = newHorizontalSpacing;
      return this;
    }
    /**
     * Gets the vertical spacing value.
     *
     * @returns {number} The vertical spacing value.
     */

  }, {
    key: "getVerticalSpacing",
    value: function getVerticalSpacing() {
      return this._verticalSpacing;
    }
    /**
     * Sets the vertical spacing value.
     *
     * @param {number} newVerticalSpacing The new vertical spacing value.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setVerticalSpacing",
    value: function setVerticalSpacing(newVerticalSpacing) {
      this._verticalSpacing = newVerticalSpacing;
      return this;
    }
    /**
     * Gets the sizing mode.
     *
     * @returns {string} The configured node sizing mode.
     */

  }, {
    key: "getSizingMode",
    value: function getSizingMode() {
      return this._sizingMode;
    }
    /**
     * Sets the sizing mode.
     *
     * @param {('nodeSize'|'size')} newSizingMode The sizing mode. Should be either 'nodeSize' to automatically size the SVG based on the nodes, or 'size' to use the configured width and height.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setSizingMode",
    value: function setSizingMode(newSizingMode) {
      this._sizingMode = newSizingMode;
      return this;
    }
  }]);

  return NodeSettings;
}();

NodeSettings.defaults = {
  sizingMode: "size",
  // set to 'nodeSize' for the tree size to automatically be based on the node dimensions itself.
  horizontalSpacing: 25,
  verticalSpacing: 25
};
/* harmony default export */ var js_NodeSettings = (NodeSettings);
// CONCATENATED MODULE: ./src/js/LoadOnDemandSettings.js
function LoadOnDemandSettings_objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; var ownKeys = Object.keys(source); if (typeof Object.getOwnPropertySymbols === 'function') { ownKeys = ownKeys.concat(Object.getOwnPropertySymbols(source).filter(function (sym) { return Object.getOwnPropertyDescriptor(source, sym).enumerable; })); } ownKeys.forEach(function (key) { LoadOnDemandSettings_defineProperty(target, key, source[key]); }); } return target; }

function LoadOnDemandSettings_defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function LoadOnDemandSettings_classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function LoadOnDemandSettings_defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function LoadOnDemandSettings_createClass(Constructor, protoProps, staticProps) { if (protoProps) LoadOnDemandSettings_defineProperties(Constructor.prototype, protoProps); if (staticProps) LoadOnDemandSettings_defineProperties(Constructor, staticProps); return Constructor; }

var LoadOnDemandSettings =
/*#__PURE__*/
function () {
  /**
   *
   * @param {object} ownerObject The owner object.
   * @param {object} options The options object.
   * @param {hasChildrenCallBack} options.hasChildren Sets the hasChildren callback function, used to determine whether a node or data item has children or not.
   * @param {loadChildrenCallBack} options.loadChildren the loadChildren callback function, used to load children data items for a node.
   */
  function LoadOnDemandSettings(ownerObject, options) {
    LoadOnDemandSettings_classCallCheck(this, LoadOnDemandSettings);

    // Define option defaults
    var mergedOptions = LoadOnDemandSettings_objectSpread({}, LoadOnDemandSettings.defaults, options);

    this._ownerObject = ownerObject;
    this._hasChildren = mergedOptions.hasChildren;
    this._loadChildren = mergedOptions.loadChildren;
  }
  /**
   * Gets the owner object.
   *
   * @returns {object} The owner object.
   */


  LoadOnDemandSettings_createClass(LoadOnDemandSettings, [{
    key: "back",
    value: function back() {
      return this._ownerObject;
    }
    /**
     * Validates whether the provided
     * settings are correct or not.
     *
     * @returns {object} The tree object.
     */

  }, {
    key: "validateSettings",
    value: function validateSettings() {
      if (!this.hasChildren && this.loadChildren) throw "With load on demand enabled, you need to define hasChildren as part of the options";
      if (!this.loadChildren && this.hasChildren) throw "With load on demand enabled, you need to define loadChildren as part of the options";
      return this;
    }
    /**
     * Load the children for a given data object.
     *
     * @param {*} data The data item, which should be used to load the children of the data item via AJAX.
     * @param {*} processData Callback function to process the children data items.
     * @returns {*}
     */

  }, {
    key: "loadChildren",
    value: function loadChildren(data, processData) {
      return this._loadChildren.call(this._ownerObject, data, processData);
    }
    /**
     * Returns a boolean indicating whether
     * the passed data item has children.
     *
     * @param {object} dataItem The data item to check if it has children or not.
     * @returns {boolean} Whether the data item has children or not.
     */

  }, {
    key: "hasChildren",
    value: function hasChildren(dataItem) {
      return this._hasChildren.call(this._ownerObject, dataItem);
    }
    /**
     * Sets the loadChildren callback function,
     * used to load children data items for
     * a node.
     *
     * @param {loadChildrenCallBack} newLoadChildrenMethod
     * @returns {object} The tree object.
     */

  }, {
    key: "setLoadChildrenMethod",
    value: function setLoadChildrenMethod(newLoadChildrenMethod) {
      this._loadChildren = newLoadChildrenMethod;
      return this;
    }
    /**
     * Sets the hasChildren callback function,
     * used to determine whether a node
     * or data item has children or not.
     *
     * @param {hasChildrenCallBack} newHasChildrenMethod
     * @returns {object} The tree object.
     */

  }, {
    key: "setHasChildrenMethod",
    value: function setHasChildrenMethod(newHasChildrenMethod) {
      this._hasChildren = newHasChildrenMethod;
      return this;
    }
    /**
     * Returns a boolean indicating whether
     * load-on-demand is enabled or not.
     *
     * @returns {boolean} Whether load-on-demand is enabled or not.
     */

  }, {
    key: "isEnabled",
    value: function isEnabled() {
      return this._hasChildren || this._loadChildren;
    }
    /**
     * Determines whether a node data item
     * has children or not.
     *
     * @callback hasChildrenCallBack
     * @param {object} dataItem Can be used to to load the childrens from the server via AJAX.
     * @returns {boolean} True if the node or data item has children to load via AJAX, false otherwise.
     */

    /**
     * Load the children items for a given
     * node data item.
     * @callback loadChildrenCallBack
     * @param {object} nodeDataItem Node data item, which can be used to to load the childrens from the server via AJAX.
     * @param {object} nodeDataItem.data The data item, which can be used to to load the childrens from the server via AJAX.
     * @param {childrenDataProcessorCallBack} processData Data processor callback function which you should use to call, passing in the children data that's been loaded via AJAX.
     * @returns {undefined}
     */

    /**
     * Processes the children items.
     * @callback childrenDataProcessorCallBack
     * @param {object[]} childrenDataItems The array of children data for the node being processed.
     * @returns {undefined}
     */

  }]);

  return LoadOnDemandSettings;
}();

LoadOnDemandSettings.defaults = {
  // Takes in a function that accepts a parameter:
  // - The node and data item which can be used
  //   to load the childrens from server
  // Returns true or false
  hasChildren: null,
  // Takes in a function that accepts two parameters:
  // - The node and data item which can be used
  //   to load the childrens from server
  // - the data processor function, which
  //   you should call, passing in the
  //   children data you loaded with
  //   your server AJAX request
  loadChildren: null
};
/* harmony default export */ var js_LoadOnDemandSettings = (LoadOnDemandSettings);
// CONCATENATED MODULE: ./src/js/BaseTree.js
function _typeof(obj) { if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { _typeof = function _typeof(obj) { return typeof obj; }; } else { _typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return _typeof(obj); }

function BaseTree_objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; var ownKeys = Object.keys(source); if (typeof Object.getOwnPropertySymbols === 'function') { ownKeys = ownKeys.concat(Object.getOwnPropertySymbols(source).filter(function (sym) { return Object.getOwnPropertyDescriptor(source, sym).enumerable; })); } ownKeys.forEach(function (key) { BaseTree_defineProperty(target, key, source[key]); }); } return target; }

function BaseTree_defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function BaseTree_classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function BaseTree_defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function BaseTree_createClass(Constructor, protoProps, staticProps) { if (protoProps) BaseTree_defineProperties(Constructor.prototype, protoProps); if (staticProps) BaseTree_defineProperties(Constructor, staticProps); return Constructor; }

function _toConsumableArray(arr) { return _arrayWithoutHoles(arr) || _iterableToArray(arr) || _nonIterableSpread(); }

function _nonIterableSpread() { throw new TypeError("Invalid attempt to spread non-iterable instance"); }

function _iterableToArray(iter) { if (Symbol.iterator in Object(iter) || Object.prototype.toString.call(iter) === "[object Arguments]") return Array.from(iter); }

function _arrayWithoutHoles(arr) { if (Array.isArray(arr)) { for (var i = 0, arr2 = new Array(arr.length); i < arr.length; i++) { arr2[i] = arr[i]; } return arr2; } }




/**
 * Recursively find a particular object within a hierarchical dataset.
 *
 * @param {object} hierarchicalObject The initial hierarchical object to start the recursive find.
 * @param {function} getChildren The callback function that gets the children items of the hierarchical object.
 * @param {function} findCondition The callback function that defines whether the object matches the condition to be returned or not.
 * @returns {object|null} The first object matching the conditions.
 */

function recursiveFind(hierarchicalObject, getChildren, findCondition) {
  if (findCondition(hierarchicalObject)) return hierarchicalObject;
  var children = getChildren(hierarchicalObject);
  var foundNode = children.find(findCondition);

  if (!foundNode) {
    var _iteratorNormalCompletion = true;
    var _didIteratorError = false;
    var _iteratorError = undefined;

    try {
      for (var _iterator = children[Symbol.iterator](), _step; !(_iteratorNormalCompletion = (_step = _iterator.next()).done); _iteratorNormalCompletion = true) {
        var child = _step.value;
        foundNode = recursiveFind(child, getChildren, findCondition);
        if (foundNode) break;
      }
    } catch (err) {
      _didIteratorError = true;
      _iteratorError = err;
    } finally {
      try {
        if (!_iteratorNormalCompletion && _iterator.return != null) {
          _iterator.return();
        }
      } finally {
        if (_didIteratorError) {
          throw _iteratorError;
        }
      }
    }
  }

  return foundNode;
}
/**
 * Recursively gets a set of objects within a hierarchical dataset.
 *
 * @param {object} hierarchicalObject The initial hierarchical object to start the recursive get.
 * @param {function} getChildren The callback function that gets the children items of the hierarchical object.
 */


function recursiveGet(hierarchicalObject, getChildren) {
  var allItems = [];
  var children = getChildren(hierarchicalObject);

  if (children) {
    var _iteratorNormalCompletion2 = true;
    var _didIteratorError2 = false;
    var _iteratorError2 = undefined;

    try {
      for (var _iterator2 = children[Symbol.iterator](), _step2; !(_iteratorNormalCompletion2 = (_step2 = _iterator2.next()).done); _iteratorNormalCompletion2 = true) {
        var child = _step2.value;
        allItems.push(child);
        var descendants = recursiveGet(child, getChildren);
        if (descendants) allItems = [].concat(_toConsumableArray(allItems), _toConsumableArray(descendants));
      }
    } catch (err) {
      _didIteratorError2 = true;
      _iteratorError2 = err;
    } finally {
      try {
        if (!_iteratorNormalCompletion2 && _iterator2.return != null) {
          _iterator2.return();
        }
      } finally {
        if (_didIteratorError2) {
          throw _iteratorError2;
        }
      }
    }
  }

  return allItems;
}

var BaseTree_BaseTree =
/*#__PURE__*/
function () {
  /**
   * @param {object} options The options object.
   * @param {string} [options.theme=default] The theme of the tree.
   * @param {boolean} [options.allowPan=true] Enables/disables the mouse drag to pan feature.
   * @param {boolean} [options.allowZoom=true] Enables/disables the mouse wheel to zoom feature.
   * @param {boolean} [options.allowFocus=true] If true, clicking on a node would focus to the node, hiding all irrelevant nodes that's not a parent, ancestor, or sibling.
   * @param {boolean} [options.allowNodeCentering=true] If true, clicking on a node would pan to the node.
   * @param {number} [options.minScale=1] Minimum zoom scaling.
   * @param {number} [options.maxScale=2] Maximum zoom scaling.
   * @param {number} [options.nodeDepthMultiplier=300] The distance between the parent and child nodes.
   * @param {boolean} [options.isFlatData=false] Indicates whether the passed data was a flat array of objects. If true, you must specify the `getParentId` option.
   * @param {getIdCallBack} options.getId
   * @param {getParentIdCallBack} [options.getParentId]
   * @param {getChildrenCallBack} [options.getChildren]
   * @param {number} [options.widthWithoutMargin=960] The width of the tree, not including the margins.
   * @param {number} [options.heightWithoutMargin=800] The height of the tree, not including the margins.
   * @param {object} [options.margin] Object specifying the margins of the tree diagram.
   * @param {number} [options.margin.top] The top margin for the tree diagram.
   * @param {number} [options.margin.right] The right margin for the tree diagram.
   * @param {number} [options.margin.bottom] The bottom margin for the tree diagram.
   * @param {number} [options.margin.left] The left margin for the tree diagram.
   * @param {number} [options.duration] Integer in milliseconds determining the duration of the animations for the tree.
   * @param {object} [options.events] Object specifying the events for the tree.
   * @param {nodeClickCallBack} [options.events.nodeClick]
   * @param {LoadOnDemandSettings} [options.loadOnDemandSettings] Object specifying the load-on-demand settings.
   * @param {NodeSettings} [options.nodeSettings] Object specifying the node settings for the tree.
   */
  function BaseTree(options) {
    BaseTree_classCallCheck(this, BaseTree);

    options = options || {}; // Defaults options to an empty object

    var mergedOptions = BaseTree_objectSpread({}, BaseTree.defaults, options); // We define our prototype properties which would be set later


    this._root = null;
    this._svg = null;
    this._panningContainer = null, this._view = null;
    this._treeGenerator = null;
    this._linkPathGenerator = null;
    this._visibleNodes = null;
    this._links = null;
    this._zoomListener = null, // Assign/Set prototype properties, using values passed from the options object
    this.setTheme(mergedOptions.theme);
    this.setData(mergedOptions.data);
    this.setElement(mergedOptions.element);
    this.setWidthWithoutMargin(mergedOptions.widthWithoutMargin);
    this.setHeightWithoutMargin(mergedOptions.heightWithoutMargin);
    this.setMargin(mergedOptions.margin);
    this.setDuration(mergedOptions.duration);
    this.setAllowPan(mergedOptions.allowPan);
    this.setAllowZoom(mergedOptions.allowZoom);
    this.setAllowFocus(mergedOptions.allowFocus);
    this.setAllowNodeCentering(mergedOptions.allowNodeCentering);
    this.setMinScale(mergedOptions.minScale);
    this.setMaxScale(mergedOptions.maxScale);
    this.setIsFlatData(mergedOptions.isFlatData);
    this.setNodeDepthMultiplier(mergedOptions.nodeDepthMultiplier); // We define our events

    if (mergedOptions.events.nodeClick) this.onNodeClick = mergedOptions.events.nodeClick; // We define our sub-prototype (AKA sub-class) properties

    this.loadOnDemandSettings = new js_LoadOnDemandSettings(this, mergedOptions.loadOnDemandSettings);
    this.nodeSettings = new js_NodeSettings(this, mergedOptions.nodeSettings); // We define our methods, which derives from our options

    this._getId = mergedOptions.getId;
    this._getChildren = mergedOptions.getChildren;
    this._getParentId = mergedOptions.getParentId;
  }
  /**
   * Defines how to create the nodes for newly
   * added data objects.
   *
   * @param {*} nodeEnter The D3 Enter selection of nodes.
   * @param {*} nodes
   * @returns {object} The tree object.
   */


  BaseTree_createClass(BaseTree, [{
    key: "_nodeEnter",
    value: function _nodeEnter(nodeEnter, nodes) {
      throw 'The function _nodeEnter must be implemented';
    }
    /**
     * Defines how to update the nodes for the
     * data objects.
     *
     * @param {*} nodeUpdate The D3 Update selection of nodes.
     * @param {*} nodeUpdateTransition The D3 transition object for the D3 Update selection of nodes.
     * @param {*} nodes
     * @returns {object} The tree object.
     */

  }, {
    key: "_nodeUpdate",
    value: function _nodeUpdate(nodeUpdate, nodeUpdateTransition, nodes) {
      throw 'The function _nodeUpdate must be implemented';
    }
    /**
     * Defines how to remove the nodes for the
     * removed data objects.
     *
     * @param {*} nodeExit The D3 Exit selection of nodes.
     * @param {*} nodeExitTransition The D3 transition object for the D3 Exit selection of nodes.
     * @param {*} nodes
     * @returns {object} The tree object.
     */

  }, {
    key: "_nodeExit",
    value: function _nodeExit(nodeExit, nodeExitTransition, nodes) {
      throw 'The function _nodeExit must be implemented';
    }
    /**
     * Gets the path generator used to render
     * the links between the nodes.
     *
     * @returns {function} The callback function that generates the SVG path coordinates for the links, given a coordinates object.
     */

  }, {
    key: "_getLinkPathGenerator",
    value: function _getLinkPathGenerator() {
      throw 'The function _getLinkPathGenerator must be implemented';
    }
    /**
     * Defines how to create the links for newly
     * added data objects.
     *
     * @param {*} source The original data object that the links are being drawn for.
     * @param {*} linkEnter The D3 Enter selection of links.
     * @param {*} links
     * @param {*} linkPathGenerator
     * @returns {object} The tree object.
     */

  }, {
    key: "_linkEnter",
    value: function _linkEnter(source, linkEnter, links, linkPathGenerator) {
      throw 'The function _linkEnter must be implemented';
    }
    /**
     * Defines how to update the links for the
     * data objects.
     *
     * @param {*} source The original data object that the links are being drawn for.
     * @param {*} linkUpdate The D3 Update selection of links.
     * @param {*} linkUpdateTransition The D3 transition object for the D3 Update selection of links.
     * @param {*} links
     * @param {*} linkPathGenerator The link path generator function.
     * @returns {object} The tree object.
     */

  }, {
    key: "_linkUpdate",
    value: function _linkUpdate(source, linkUpdate, linkUpdateTransition, links, linkPathGenerator) {
      throw 'The function _linkUpdate must be implemented';
    }
    /**
     * Defines how to remove the links for the
     * removed data objects.
     *
     * @param {object} source The original data object that the links are being drawn for.
     * @param {*} linkExit The D3 Exit selection of links.
     * @param {*} linkExitTransition The D3 transition object for the D3 Update selection of links.
     * @param {*} links
     * @param {*} linkPathGenerator The link path generator function.
     * @returns {object} The tree object.
     */

  }, {
    key: "_linkExit",
    value: function _linkExit(source, linkExit, linkExitTransition, links, linkPathGenerator) {
      throw 'The function _linkExit must be implemented';
    }
    /**
     * Called when updating dimensions when
     * node settings is configured to be
     * 'nodesize'.
     *
     * @returns {number[]} An array with two values, representing the height and width of the node respectively.
     */

  }, {
    key: "_getNodeSize",
    value: function _getNodeSize() {
      throw 'The function _getNodeSize must be implemented';
    }
    /**
     * Focuses and expands all the way through to a node.
     *
     * @param {*} idOrNodeDataItem The id of the node to focus, or the node data item object.
     * @returns {object} The tree object.
     */

  }, {
    key: "focusToNode",
    value: function focusToNode(idOrNodeDataItem) {
      this.removeSelection(this.getRoot());
      var nodeDataItem = idOrNodeDataItem;
      if (_typeof(nodeDataItem) !== 'object' && nodeDataItem !== null) nodeDataItem = this.getNode(nodeDataItem);
      var parentNode = null; // Expand every parent/ancestor node

      parentNode = nodeDataItem.parent;

      while (parentNode) {
        if (parentNode._children) this.expand(parentNode);
        parentNode = parentNode.parent;
      }

      if (this.getAllowFocus()) {
        // Hide the parent/ancestor node siblings
        parentNode = nodeDataItem.parent;

        while (parentNode) {
          this.hideSiblings(parentNode);
          parentNode = parentNode.parent;
        }

        this.updateTreeWithFocusOnNode(nodeDataItem);
        nodeDataItem.selected = true;
      }

      this.update(this.getRoot());
      this.centerNode(nodeDataItem);
      return this;
    }
    /**
     * Attaches a handler to the event.
     * Note you can only attach one handler
     * to an event at this stage.
     *
     * @param {string} event The event name.
     * @param {function} handler A callback function that executes when the event is triggerred.
     * @returns {object} The tree object.
     */

  }, {
    key: "on",
    value: function on(event, handler) {
      if (event.indexOf("on") == 0) event.slice(2); // Remove the "on"

      var pascalCasedEventName = event.charAt(0).toUpperCase() + event.slice(1);
      this["on" + pascalCasedEventName] = handler;
      return this;
    }
    /**
     * Triggers all handlers associated with an event.
     *
     * @param {string} event The event name.
     * @param {...object} [args] The arguments supplied to the event.
     * @returns {*} The returned value of the triggered handler.
     */

  }, {
    key: "emit",
    value: function emit(event) {
      if (event.indexOf("on") == 0) event.slice(2); // Remove the "on"

      var pascalCasedEventName = event.charAt(0).toUpperCase() + event.slice(1);
      var handler = this["on" + pascalCasedEventName];

      for (var _len = arguments.length, args = new Array(_len > 1 ? _len - 1 : 0), _key = 1; _key < _len; _key++) {
        args[_key - 1] = arguments[_key];
      }

      if (handler) return handler.apply(this, args);
    }
    /**
     * Returns a boolean whether the
     * tree is using flat data or not.
     *
     * @returns {boolean} Whether the tree is using flat data or not.
     */

  }, {
    key: "getIsFlatData",
    value: function getIsFlatData() {
      return this._isFlatData;
    }
    /**
     * Sets the is flat data flag.
     * If set to true, you must specify
     * the `getParentId` option.
     *
     * @param {boolean} newIsFlatData Whether the tree is using flat data or not.
     */

  }, {
    key: "setIsFlatData",
    value: function setIsFlatData(newIsFlatData) {
      this._isFlatData = newIsFlatData;
      return this;
    }
    /**
     * Regenerates the node data.
     *
     * @returns {object} The tree object.
     */

  }, {
    key: "regenerateNodeData",
    value: function regenerateNodeData() {
      var _this = this;

      // Assigns parent, children, height, depth
      if (!this.getIsFlatData()) {
        if (!this._getChildren) throw "If you are providing hierarchical structured data, then you must set the getChildren accessor property."; // Specify your children property here,
        // so that D3's resulting root object
        // has a mapping from its "children" property
        // to your specified children property

        this._root = CustomD3.hierarchy(this.getData(), function (data) {
          return _this.getChildren.call(_this, data);
        });
      } else {
        if (!this._getParentId) throw "If you are providing flat structured data, then you must set the getParentId accessor property."; // stratifier is a function that would convert the flat
        // dataset into hierarchically structured data
        // to be used with D3 trees.
        // It accepts the dataset as its parameter,
        // and returns the converted data.
        // Note that this is used instead of the d3.hierarchy()
        // method as d3.hierarchy() should only be used if the
        // data is already in heirarchical structure, and
        // needs to be converted to D3 hierarchical nodes

        var stratifier = CustomD3.stratify().id(function (data, index, arr) {
          return _this.getId.call(_this, data);
        }).parentId(function (data, index, arr) {
          return _this.getParentId.call(_this, data);
        });
        this._root = stratifier(this.getData());
      }

      return this;
    }
    /**
     * @returns {string} The theme the tree is using.
     */

  }, {
    key: "getTheme",
    value: function getTheme() {
      return this._theme;
    }
    /**
     * Sets the tree theme.
     *
     * @param {string} theme The theme to set the tree to.
     * @returns {object} The tree object.
     */

  }, {
    key: "setTheme",
    value: function setTheme(theme) {
      this._theme = theme;
      return this;
    }
    /**
     * Gets the data items used to render
     * the nodes.
     *
     * @returns {object[]} The array of data items the tree uses.
     */

  }, {
    key: "getData",
    value: function getData() {
      return this._data;
    }
    /**
     * Sets the data items the tree should
     * use to render the nodes.
     *
     * @param {object[]} newData The new set of data items.
     * @returns {object} The tree object.
     */

  }, {
    key: "setData",
    value: function setData(newData) {
      this._data = newData;
      return this;
    }
    /**
     * Gets the node depth multiplier that
     * affects the distance between the
     * parent node and the child node.
     *
     * @returns {number} The node depth multiplier value
     */

  }, {
    key: "getNodeDepthMultiplier",
    value: function getNodeDepthMultiplier() {
      return this._nodeDepthMultiplier;
    }
    /**
     * Sets the node depth multiplier value.
     *
     * @param {number} newNodeDepthMultiplier The value that affects the distance between the parent node and the child node.
     * @returns {object} The tree object.
     */

  }, {
    key: "setNodeDepthMultiplier",
    value: function setNodeDepthMultiplier(newNodeDepthMultiplier) {
      this._nodeDepthMultiplier = newNodeDepthMultiplier;
      return this;
    }
    /**
     * Gets the duration of animations
     * for the tree.
     *
     * @returns {number} The animation duration in milliseconds.
     */

  }, {
    key: "getDuration",
    value: function getDuration() {
      return this._duration;
    }
    /**
     * Sets the duration of animations
     * for the tree.
     *
     * @param {*} newDuration The animation duration in milliseconds.
     * @returns {object} The tree object.
     */

  }, {
    key: "setDuration",
    value: function setDuration(newDuration) {
      this._duration = newDuration;
      return this;
    }
    /**
     * Gets the boolean value indicating
     * whether the drag-to-pan pan feature
     * is enabled or not.
     *
     * @returns {boolean} Whether panning is enabled or not.
     */

  }, {
    key: "getAllowPan",
    value: function getAllowPan() {
      return this._allowPan;
    }
    /**
     * Sets the boolean value indicating
     * whether the drag-to-pan pan feature
     * is enabled or not.
     *
     * @param {*} newAllowPan Whether panning is enabled or not.
     * @returns {object} The tree object.
     */

  }, {
    key: "setAllowPan",
    value: function setAllowPan(newAllowPan) {
      this._allowPan = newAllowPan;
      return this;
    }
    /**
     * Gets the boolean value indicating
     * whether the mouse wheel to zoom in/out
     * feature is enabled or not.
     *
     * @returns {boolean} Whether zooming is enabled or not.
     */

  }, {
    key: "getAllowZoom",
    value: function getAllowZoom() {
      return this._allowZoom;
    }
    /**
     * Sets the boolean value indicating
     * whether the mouse wheel to zoom in/out
     * feature is enabled or not.
     *
     * @param {boolean} newAllowZoom Whether zooming is enabled or not.
     * @returns {object} The tree object.
     */

  }, {
    key: "setAllowZoom",
    value: function setAllowZoom(newAllowZoom) {
      this._allowZoom = newAllowZoom;
      return this;
    }
    /**
     * Gets the boolean value indicating
     * whether to focus to the clicked node
     * or not. Focusing on a node would hide
     * all irrelevant nodes that's not a
     * parent, sibling or ancestor of the
     * clicked node.
     *
     * @returns {boolean} Whether to focus to the clicked node.
     */

  }, {
    key: "getAllowFocus",
    value: function getAllowFocus() {
      return this._allowFocus;
    }
    /**
     * Sets the boolean value indicating
     * whether to pan to the clicked node
     * feature is enabled or not.
     *
     * @param {boolean} newAllowFocus Whether to pan to the clicked node.
     * @returns {object} The tree object.
     */

  }, {
    key: "setAllowFocus",
    value: function setAllowFocus(newAllowFocus) {
      this._allowFocus = newAllowFocus;
      return this;
    }
    /**
     * Gets the boolean value indicating
     * whether to pan to a clicked node.
     *
     * @returns {boolean} Whether to pan to the clicked node.
     */

  }, {
    key: "getAllowNodeCentering",
    value: function getAllowNodeCentering() {
      return this._allowNodeCentering;
    }
    /**
     * Whether to pan to a clicked node.
     *
     * @param {boolean} newAllowNodeCentering Whether to pan to the clicked node.
     * @returns {object} The tree object.
     */

  }, {
    key: "setAllowNodeCentering",
    value: function setAllowNodeCentering(newAllowNodeCentering) {
      this._allowNodeCentering = newAllowNodeCentering;
      return this;
    }
    /**
     * Gets the minimum zoom scaling.
     *
     * @returns {number} The minimum zoom scale value.
     */

  }, {
    key: "getMinScale",
    value: function getMinScale() {
      return this._minScale;
    }
    /**
     * Sets the minimum zoom scaling.
     *
     * @param {*} newMinScale The minimum zoom scale value.
     * @returns {object} The tree object.
     */

  }, {
    key: "setMinScale",
    value: function setMinScale(newMinScale) {
      this._minScale = newMinScale;
      return this;
    }
    /**
     * Gets the maximum zoom scaling.
     *
     * @returns {number} Maximum zoom scale value.
     */

  }, {
    key: "getMaxScale",
    value: function getMaxScale() {
      return this._maxScale;
    }
    /**
     * Sets the maximum zoom scaling.
     *
     * @param {*} newMaxScale The maximum zoom scale value.
     * @returns {object} The tree object.
     */

  }, {
    key: "setMaxScale",
    value: function setMaxScale(newMaxScale) {
      this._maxScale = newMaxScale;
      return this;
    }
    /**
     * Gets the load on demand settings object.
     *
     * @returns {LoadOnDemandSettings} The load on demand settings.
     */

  }, {
    key: "getLoadOnDemandSettings",
    value: function getLoadOnDemandSettings() {
      return this.loadOnDemandSettings;
    }
    /**
     * Gets the node settings object.
     *
     * @returns {NodeSettings} The node settings.
     */

  }, {
    key: "getNodeSettings",
    value: function getNodeSettings() {
      return this.nodeSettings;
    }
    /**
     * Gets the container DOM element.
     *
     * @returns {object} The container DOM element.
     */

  }, {
    key: "getElement",
    value: function getElement() {
      return this._element;
    }
    /**
     * Sets the container DOM element
     *
     * @param {object} newElement The container DOM element.
     * @returns {object} The tree object.
     */

  }, {
    key: "setElement",
    value: function setElement(newElement) {
      this._element = newElement;
      return this;
    }
    /**
     * Gets the root node object.
     *
     * @return {object} The root D3 tree node object.
     */

  }, {
    key: "getRoot",
    value: function getRoot() {
      return this._root;
    }
    /**
     * Gets the D3 selection object for the SVG element.
     *
     * @return {object} Returns the D3 selection object.
     */

  }, {
    key: "getSvg",
    value: function getSvg() {
      return this._svg;
    }
    /**
     * Gets the D3 selection object for the view element.
     *
     * @returns {object} D3 selection object for the view element.
     */

  }, {
    key: "getView",
    value: function getView() {
      return this._view;
    }
    /**
     * Gets the D3 selection object for the
     * panning container element.
     *
     * @returns {object} D3 selection object for the panning container element.
     */

  }, {
    key: "getPanningContainer",
    value: function getPanningContainer() {
      return this._panningContainer;
    }
    /**
     * Gets the D3 generator object used to
     * generate the tree nodes coordinates.
     *
     * @returns {function} D3 tree generator object.
     */

  }, {
    key: "getTreeGenerator",
    value: function getTreeGenerator() {
      return this._treeGenerator;
    }
    /**
     * Get a single node given an id or a data item.
     *
     * @param {*|object} idOrDataItem The ID or data item to retrieve the D3 tree node data item with.
     * @returns {object} D3 tree node data item.
     */

  }, {
    key: "getNode",
    value: function getNode(idOrDataItem) {
      var _this2 = this;

      var id = idOrDataItem;
      if (_typeof(id) === 'object' && id !== null) id = this.getId(id);
      var rootNode = this.getRoot();

      var getNodeChildren = function getNodeChildren(node) {
        if (node._children) return node._children;
        return [];
      };

      var node = recursiveFind(rootNode, getNodeChildren, function (x) {
        return _this2.getId(x.data) == id;
      });
      return node;
    }
    /**
     * Get a single data item given an id.
     *
     * @param {*} id The ID to retrieve the data item with.
     * @returns {object} The data item with the given ID.
     */

  }, {
    key: "getDataItem",
    value: function getDataItem(id) {
      var node = this.getNode(id);
      return node.data;
    }
    /**
     * Get the array of D3 node data items
     * the D3 tree has generated.
     *
     * @returns {object[]} Array of D3 node data items.
     */

  }, {
    key: "getNodes",
    value: function getNodes() {
      return this._nodes;
    }
    /**
     * Get the array of visible D3 node
     * data items the D3 tree has generated.
     *
     * @returns {object[]} Array of D3 node data items.
     */

  }, {
    key: "getVisibleNodes",
    value: function getVisibleNodes() {
      return this._visibleNodes;
    }
    /**
     * Get the array of D3 link data items
     * the D3 tree has generated.
     *
     * @returns {object[]} Array of D3 link data items.
     */

  }, {
    key: "getLinks",
    value: function getLinks() {
      return this._links;
    }
    /**
     * Gets the D3 zoom listener used for
     * the panning, zooming and focus features.
     *
     * @returns {function} The D3 zoom listener
     */

  }, {
    key: "getZoomListener",
    value: function getZoomListener() {
      return this._zoomListener;
    }
    /**
     * Gets the ID for a given data item.
     *
     * @param {object} dataItem The data item to get the ID from.
     * @returns {*} The ID for the given data item.
     */

  }, {
    key: "getId",
    value: function getId(dataItem) {
      return this._getId(dataItem);
    }
    /**
     * Gets the children data items for a given data item.
     *
     * @param {object} dataItem The data item to get the children data items from.
     * @returns {object[]} The array of child data items.
     */

  }, {
    key: "getChildren",
    value: function getChildren(dataItem) {
      return this._getChildren(dataItem);
    }
    /**
     * Gets the parent ID for a given data item.
     *
     * @param {object} dataItem The data item to get the parent ID from.
     * @returns {*} The parent ID for the given data item.
     */

  }, {
    key: "getParentId",
    value: function getParentId(dataItem) {
      return this._getParentId(dataItem);
    }
    /**
     * Sets the ID accessor callback function,
     * defining how to get a unique ID from a
     * given data item.
     *
     * @param {getIdCallBack} newIdAccessor Callback function to get the ID for a given data item.
     * @returns {object} The tree object.
     */

  }, {
    key: "setIdAccessor",
    value: function setIdAccessor(newIdAccessor) {
      this._getId = newIdAccessor;
      return this;
    }
    /**
     * Sets the children accessor callback function,
     * defining how to get the children data items
     * from a given data item.
     *
     * @param {getChildrenCallBack} newChildrenAccessor Callback function to get the children for a given data item.
     * @returns {object} The tree object.
     */

  }, {
    key: "setChildrenAccessor",
    value: function setChildrenAccessor(newChildrenAccessor) {
      this._getChildren = newChildrenAccessor;
      return this;
    }
    /**
     * Sets the parent ID accessor callback function,
     * defining how to get the parent ID from a
     * given data item.
     *
     * @param {getParentIdCallBack} newParentIdAccessor Callback function to get the parent id for a given data item.
     * @returns {object} The tree object.
     */

  }, {
    key: "setParentIdAccessor",
    value: function setParentIdAccessor(newParentIdAccessor) {
      this._getParentId = newParentIdAccessor;
      return this;
    }
    /**
     * Gets the width of SVG, including the margins.
     *
     * @returns {number} The width of the SVG.
     */

  }, {
    key: "getWidth",
    value: function getWidth() {
      return this.getWidthWithoutMargin() - this.getMargin().left - this.getMargin().right;
    }
    /**
     * Gets the height of SVG, including the margins.
     *
     * @returns {number} The height of the SVG.
     */

  }, {
    key: "getHeight",
    value: function getHeight() {
      return this.getHeightWithoutMargin() - this.getMargin().top - this.getMargin().bottom;
    }
    /**
     * Sets the margins for the tree diagram.
     *
     * @param {object} newMargins The margin object.
     * @param {number} newMargins.top The margin top for the tree diagram.
     * @param {number} newMargins.right The margin right for the tree diagram.
     * @param {number} newMargins.bottom The margin bottom for the tree diagram.
     * @param {number} newMargins.left The margin left for the tree diagram.
     * @returns {object} The tree object.
     */

  }, {
    key: "setMargin",
    value: function setMargin(newMargins) {
      this._margin = newMargins;
      return this;
    }
    /**
     * Gets the margins for the tree diagram.
     *
     * @returns {object} The margins object.
     */

  }, {
    key: "getMargin",
    value: function getMargin() {
      return this._margin;
    }
    /**
     * Sets the width of the SVG for the tree diagram.
     *
     * @param {*} newWidthWithoutMargin The width of SVG for the tree diagram.
     * @returns {object} The tree object.
     */

  }, {
    key: "setWidthWithoutMargin",
    value: function setWidthWithoutMargin(newWidthWithoutMargin) {
      this._widthWithoutMargin = newWidthWithoutMargin;
      return this;
    }
    /**
     * Gets the width of the SVG for the tree diagram.
     * Does not include the margins.
     *
     * @returns {number} The width (not including the margins) of the SVG for the tree diagram.
     */

  }, {
    key: "getWidthWithoutMargin",
    value: function getWidthWithoutMargin() {
      return this._widthWithoutMargin;
    }
    /**
     * Sets the height of the SVG for the tree diagram.
     *
     * @param {*} newHeightWithoutMargin The height of SVG for the tree diagram.
     * @returns {object} The tree object.
     */

  }, {
    key: "setHeightWithoutMargin",
    value: function setHeightWithoutMargin(newHeightWithoutMargin) {
      this._heightWithoutMargin = newHeightWithoutMargin;
      return this;
    }
    /**
     * Gets the height of the SVG for the tree diagram.
     * Does not include the margins.
     *
     * @returns {number} The height (not including the margins) of the SVG for the tree diagram.
     */

  }, {
    key: "getHeightWithoutMargin",
    value: function getHeightWithoutMargin() {
      return this._heightWithoutMargin;
    }
    /**
     * Updates the dimensions of the SVG.
     *
     * @returns {object} The tree object.
     */

  }, {
    key: "updateDimensions",
    value: function updateDimensions() {
      // Update SVG with new width and height
      this.getSvg() // Use viewBox to set SVG width and height
      // so it is responsive, and can be resized
      // based on the parent element
      .attr("viewBox", "0 0 " + this.getWidthWithoutMargin() + " " + this.getHeightWithoutMargin());
      var margin = this.getMargin();
      var needToCenterView = false; // update the tree generator with the new width and height

      var sizingMode = this.nodeSettings.getSizingMode();
      if (typeof sizingMode === 'string') sizingMode = sizingMode.trim().toLowerCase();

      if (sizingMode === "nodesize") {
        this.getTreeGenerator().nodeSize(this._getNodeSize()); // Only perform centering if node centering is turned off,
        // as that would center to the root node anyway. Node
        // centering is turned on when allow focus is turned on.

        if (this.getAllowFocus() === false) needToCenterView = true;
      } else {
        this.getTreeGenerator().size([this.getHeight(), this.getWidth()]);
      } // If we need to center the tree by adjusting the view and the node position


      if (needToCenterView === false) {
        // Update the view with the new margins
        this.getView().attr("transform", "translate(" + margin.left + "," + margin.top + ")");
        this.getRoot().x0 = this.getHeight() / 2;
      } else {
        // Move the view downwards as to center the root node
        // This is due to when you use node-size, it sets the
        // node origin at 0, 0 instead of automatically
        // centering it as it does with size()
        this.getView().attr("transform", "translate(" + margin.left + ", " + (this.getHeight() / 2 + this.getMargin().top) + ")");
        this.getRoot().x0 = 0;
      }

      if (this.getZoomListener()) {
        this.getZoomListener().extent([[0, 0], [this.getWidthWithoutMargin(), this.getHeightWithoutMargin()]]);
      }

      this.getRoot().y0 = 0;
      return this;
    }
    /**
     * Validates the settings to ensure the
     * tree diagram is ready to be generated.
     *
     * @returns {object} The tree object.
     */

  }, {
    key: "validateSettings",
    value: function validateSettings() {
      // Check to make sure compulsory options are provided
      if (!this.getElement()) throw "Need to pass in an element as part of the options";
      if (!this.getData()) throw "Need to pass in data as part of the options"; // Checks if mandatory methods to specify exists

      if (!this._getId) throw "Need to define the getId function as part of the options";
      this.loadOnDemandSettings.validateSettings();
      return this;
    }
    /**
     * Creates and set up the the tree diagram.
     *
     * @returns {object} The tree object.
     */

  }, {
    key: "initialize",
    value: function initialize() {
      var _this3 = this;

      this.validateSettings();
      this.regenerateNodeData();

      while (this.getElement().firstChild) {
        this.getElement().removeChild(this.getElement().firstChild);
      }

      ; // Create the svg, and set its dimensions

      this._svg = CustomD3.select(this.getElement()).append("svg").classed('mitch-d3-tree', true).classed(this.getTheme(), true).attr("preserveAspectRatio", "xMidYMid meet").style("width", "100%").style("height", "100%"); // Create the view with margins

      this._view = this.getSvg().append("g").classed("view", true); // Create tree generator to position the nodes

      this._treeGenerator = CustomD3.tree(); // Create the panning container which panning should act upon

      this._panningContainer = this.getView().append("g").classed("panningContainer", true);
      this._zoomListener = CustomD3.zoom() // Limit zoom level
      .scaleExtent([this.getMinScale(), this.getMaxScale()]) // Zoom in D3 translates to the native HTML/JS events of:
      // - Double Clicking (i.e. to zoom in)
      // - Dragging (i.e. panning or moving around)
      // - Wheel (i.e. zoom in/out)
      .on("zoom", function () {
        // The "zoom" event populates d3.event with an object that has
        // a "transform" property (an object with three properties
        // of x, y, and k), where x and y is for translation purposes,
        // and k is the scaling factor
        var transform = CustomD3.event.transform;

        _this3.getPanningContainer().attr("transform", transform);
      });
      this.getSvg().call(this.getZoomListener());

      if (this.getAllowPan() === false) {
        this.getSvg().on("mousedown.zoom", null).on("touchstart.zoom", null).on("touchmove.zoom", null).on("touchend.zoom", null);
      }

      if (this.getAllowZoom() === false) {
        this.getSvg().on("dblclick.zoom", null).on("wheel.zoom", null);
      }

      this.updateDimensions();

      this._populateUnderlyingChildren(this.getRoot());

      if (this.getRoot().children) this.getRoot().children.forEach(this.collapseRecursively);
      this.removeSelection(this.getRoot()); // Call the first update, which renders
      // the initial tree

      this.update(this.getRoot()); // Centers the root node

      this.centerNode(this.getRoot());
      return this;
    }
    /**
     * Expands the given node data item.
     *
     * @param {object} nodeDataItem The D3 node data item to expand.
     * @returns {object} The tree object.
     */

  }, {
    key: "expand",
    value: function expand(nodeDataItem) {
      nodeDataItem.children = nodeDataItem._children;
      return this;
    }
    /**
     * Expands the given node data item,
     * and its children and descendants.
     *
     * @param {object} nodeDataItem The D3 node data item to expand.
     * @returns {object} The tree object.
     */

  }, {
    key: "expandRecursively",
    value: function expandRecursively(nodeDataItem) {
      var rec = function recursive(directNodeDataItem) {
        if (directNodeDataItem.children) {
          directNodeDataItem.children.forEach(recursive);
          directNodeDataItem.children = directNodeDataItem._children;
        }
      };

      rec(nodeDataItem);
      return this;
    }
    /**
     * Collapses the given node data item.
     *
     * @param {object} nodeDataItem The D3 node data item to collapse.
     * @returns {object} The tree object.
     */

  }, {
    key: "collapse",
    value: function collapse(nodeDataItem) {
      nodeDataItem.children = null;
      return this;
    }
    /**
     * Collapses the given node data item,
     * and its children and descendants.
     *
     * @param {object} nodeDataItem The D3 node data item to collapse.
     * @returns {object} The tree object.
     */

  }, {
    key: "collapseRecursively",
    value: function collapseRecursively(nodeDataItem) {
      var rec = function recursive(directNodeDataItem) {
        if (directNodeDataItem.children) {
          directNodeDataItem.children.forEach(recursive);
          directNodeDataItem.children = null;
        }
      };

      rec(nodeDataItem);
      return this;
    }
    /**
     * Populates the node's children to a hidden property.
     *
     * @param {object} nodeDataItem The D3 node data item to collapse.
     * @returns {object} The tree object.
     */

  }, {
    key: "_populateUnderlyingChildren",
    value: function _populateUnderlyingChildren(nodeDataItem) {
      var rec = function recursive(directNodeDataItem) {
        if (directNodeDataItem.children) {
          directNodeDataItem._children = directNodeDataItem.children;

          directNodeDataItem._children.forEach(recursive);
        }
      };

      rec(nodeDataItem);
      return this;
    }
    /**
     * Remove node selections for a given node and it's children.
     *
     * @param {object} nodeDataItem The D3 node data item to remove selection from.
     * @returns {object} The tree object.
     */

  }, {
    key: "removeSelection",
    value: function removeSelection(nodeDataItem) {
      var rec = function recursive(directNodeDataItem) {
        directNodeDataItem.selected = false;

        if (directNodeDataItem.children) {
          directNodeDataItem.children.forEach(recursive);
        }
      };

      rec(nodeDataItem);
      return this;
    }
    /**
     * Center the view to a D3 tree node.
     *
     * @param {*} nodeDataItem The D3 node data item to focus on.
     * @returns {object} The tree object.
     */

  }, {
    key: "centerNode",
    value: function centerNode(nodeDataItem) {
      var transform = CustomD3.zoomTransform(this.getSvg().node());
      var scale = transform.k;
      var x = -nodeDataItem.y0;
      var y = -nodeDataItem.x0;
      var translateX = x * scale + this.getWidth() / 4;
      var translateY = y * scale + this.getHeight() / 2;
      this.getSvg().transition().duration(this.getDuration()).call(this.getZoomListener().transform, CustomD3.zoomIdentity.translate(translateX, translateY).scale(scale));
      return this;
    }
    /**
     * Triggers the nodeClick event when a
     * D3 node is clicked on, and proceeds
     * to focus/expand/collapse the node.
     *
     * @param {object} nodeDataItem The D3 node data item that was clicked.
     * @param {number} index The index of the D3 node being clicked in the array of siblings.
     * @param {object[]} arr Array of siblings D3 node, inclusive of the clicked node data item itself.
     * @returns {boolean} True meaning it successfully focused/expanded/collapsed a node. False otherwise.
     */

  }, {
    key: "_onNodeClick",
    value: function _onNodeClick(nodeDataItem, index, arr) {
      var continueFocus = true;
      continueFocus = this.emit('nodeClick', nodeDataItem, index, arr);
      if (continueFocus === false) return false;
      if (this.getAllowFocus()) this.nodeFocus.call(this, nodeDataItem);else this.nodeToggle.call(this, nodeDataItem);
      return true;
    }
    /**
     * Creates a child D3 tree node.
     *
     * @param {object} parentNodeDataItem The parent D3 tree node data item.
     * @param {object} dataItem The data item.
     * @returns {object} The newly created D3 node;
     */

  }, {
    key: "_createNode",
    value: function _createNode(parentNodeDataItem, dataItem) {
      // Create a D3 node object from resulting data items using d3.hierarchy()
      var newNode = CustomD3.hierarchy(dataItem); // Now add missing properties to Node like child, parent, depth

      newNode.depth = parentNodeDataItem.depth + 1;
      newNode.height = parentNodeDataItem.height - 1;
      newNode.parent = parentNodeDataItem;
      newNode.id = this.getId.call(this, dataItem);
      return newNode;
    }
    /**
     * Creates and adds a child D3 tree
     * node to a given parent D3 tree node.
     *
     * @param {object} parentNodeDataItem The parent D3 tree node data item.
     * @param {object} dataItem The data item.
     * @returns {object} The newly created and added D3 node;
     */

  }, {
    key: "_addUnderlyingChildNode",
    value: function _addUnderlyingChildNode(parentNodeDataItem, dataItem) {
      var newNode = this._createNode(parentNodeDataItem, dataItem);

      parentNodeDataItem._children.push(newNode);

      return newNode;
    }
    /**
     * Process the loaded data from AJAX
     * resulting from a node expand.
     *
     * @param {object} nodeDataItem The D3 node data item being expanded.
     * @param {object[]} result The children data items to process.
     * @returns {object} The tree object.
     */

  }, {
    key: "_processLoadedDataForNodeFocus",
    value: function _processLoadedDataForNodeFocus(nodeDataItem, result) {
      var _this4 = this;

      nodeDataItem._children = [];
      result.forEach(function (currentItem) {
        return _this4._addUnderlyingChildNode(nodeDataItem, currentItem);
      });

      this._populateUnderlyingChildren(nodeDataItem);

      this.updateTreeWithFocusOnNode(nodeDataItem);
      var wasSelected = nodeDataItem.selected;
      this.removeSelection(this.getRoot());
      nodeDataItem.selected = true;
      this.update(nodeDataItem);
      if (this.getAllowNodeCentering() === true && (wasSelected === false || typeof wasSelected === 'undefined')) this.centerNode(nodeDataItem);
      return this;
    }
    /**
     * Focuses to a node, given a node data item.
     *
     * @param {object} nodeDataItem The node being focused on.
     * @returns {object} The tree object.
     */

  }, {
    key: "nodeFocus",
    value: function nodeFocus(nodeDataItem) {
      var _this5 = this;

      if (!nodeDataItem.children && !nodeDataItem._children && this.loadOnDemandSettings.isEnabled() && this.loadOnDemandSettings.hasChildren(nodeDataItem.data)) {
        var processData = function processData(result) {
          return _this5._processLoadedDataForNodeFocus(nodeDataItem, result);
        };

        this.loadOnDemandSettings.loadChildren(nodeDataItem.data, processData);
      } else {
        this.updateTreeWithFocusOnNode(nodeDataItem);
        var wasSelected = nodeDataItem.selected;
        this.removeSelection(this.getRoot());
        nodeDataItem.selected = true;
        this.update(nodeDataItem);
        if (this.getAllowNodeCentering() === true && (wasSelected === false || typeof wasSelected === 'undefined')) this.centerNode(nodeDataItem);
      }

      return this;
    }
    /**
     * Process the loaded data from AJAX
     * resulting from a node toggle.
     *
     * @param {object} nodeDataItem The D3 node data item.
     * @param {object[]} result Array of sibling node data items, inclusive the node being toggled.
     * @returns {object} The tree object.
     */

  }, {
    key: "_processLoadedDataForNodeToggle",
    value: function _processLoadedDataForNodeToggle(nodeDataItem, result) {
      var _this6 = this;

      nodeDataItem._children = [];
      result.forEach(function (currentItem) {
        return _this6._addUnderlyingChildNode(nodeDataItem, currentItem);
      });
      this.expand(nodeDataItem);
      this.update(nodeDataItem);
      if (this.getAllowNodeCentering() === true) this.centerNode(nodeDataItem);
      return this;
    }
    /**
     * Toggles the children visibility for a given node data item.
     *
     * @param {*} nodeDataItem D3 Node data item.
     * @returns {object} The tree object.
     */

  }, {
    key: "nodeToggle",
    value: function nodeToggle(nodeDataItem) {
      var _this7 = this;

      // If it hasn't been loaded, and it's specified to have children,
      // then perform load-on-demand to load new items from server
      // and add them as child nodes
      if (!nodeDataItem.children && !nodeDataItem._children && this.loadOnDemandSettings.isEnabled() && this.loadOnDemandSettings.hasChildren(nodeDataItem.data)) {
        var processData = function processData(result) {
          return _this7._processLoadedDataForNodeToggle(nodeDataItem, result);
        };

        this.loadOnDemandSettings.loadChildren(nodeDataItem.data, processData);
      } else {
        if (nodeDataItem.children) this.collapse(nodeDataItem);else this.expand(nodeDataItem);
        this.update(nodeDataItem);
        if (this.getAllowNodeCentering() === true) this.centerNode(nodeDataItem);
      }

      return this;
    }
    /**
     * Hide the siblings nodes
     * for a given node.
     *
     * @param {object} nodeDataItem The D3 node to hide siblings for.
     * @returns {object} The tree object.
     */

  }, {
    key: "hideSiblings",
    value: function hideSiblings(nodeDataItem) {
      var _this8 = this;

      var parentNode = nodeDataItem.parent;

      if (parentNode) {
        var nodeId = this.getId(nodeDataItem.data);
        parentNode.children.filter(function (x) {
          return _this8.getId(x.data) != nodeId;
        }).forEach(this.collapseRecursively);
        parentNode.children = [];
        parentNode.children.push(nodeDataItem);
      }

      return this;
    }
    /**
     * Updates the tree diagram so only the relevant
     * focused node and direct parent hierarchies are
     * shown.
     *
     * @param {object} nodeDataItem D3 Node data item.
     * @returns {object} The tree object.
     */

  }, {
    key: "updateTreeWithFocusOnNode",
    value: function updateTreeWithFocusOnNode(nodeDataItem) {
      if (!nodeDataItem.children && nodeDataItem._children) {
        // If there's no children nodes, but there a some children items to expand
        this.hideSiblings(nodeDataItem);
        this.expand(nodeDataItem); // Collapse the current focused node's children, so only direct childrens are shown

        nodeDataItem.children.forEach(this.collapseRecursively);
      } else if (nodeDataItem.children) {
        // If there are rendered children nodes
        // Checks if its children has any rendered children
        var hasNestedChildren = nodeDataItem.children.some(function (currentItem, index, arr) {
          return currentItem.children;
        });
        var isPreviouslyExpandedNode = !hasNestedChildren; // If it is a parent node with children, and
        // is not the previous expanded node,
        // then we'll focus on it, expanding it
        // and showing all of its children

        if (isPreviouslyExpandedNode === false) {
          this.collapseRecursively(nodeDataItem);
          this.expand(nodeDataItem);
        }
      }

      return this;
    }
    /**
     * Updates the tree nodes given
     * a D3 tree node.
     *
     * @param {object} nodeDataItem The D3 node data item to update.
     * @param {object[]} nodes Array of D3 node data items.
     * @returns {object} The tree object.
     */

  }, {
    key: "_updateNodes",
    value: function _updateNodes(nodeDataItem, nodes) {
      var _this9 = this;

      // Normalize for fixed-depth.
      // You can increase the depth multiplication to get more depth,
      // i.e. increasing the distance between the parent node and child node
      nodes.forEach(function (data) {
        return data.y = data.depth * _this9.getNodeDepthMultiplier();
      }); // ****************** Nodes section ***************************
      // Update the nodes...

      var nodes = this.getPanningContainer().selectAll("g.node") // The second parameter of data() takes in a
      // function, determining the key of the data
      // items, which is useful to retrieve items,
      // and databind them
      .data(nodes, function (data) {
        return _this9.getId.call(_this9, data.data);
      }); // Enter any new nodes at the parent's previous position.

      var nodeEnter = nodes.enter().append("g").classed("node", true).attr("transform", function (data, index, arr) {
        // Translating while inverting X/Y to
        // make tree direction from left to right,
        // instead of the typical top-to-down tree
        return "translate(" + nodeDataItem.y0 + "," + nodeDataItem.x0 + ")";
      }).on("click", function (data, index, arr) {
        return _this9._onNodeClick.call(_this9, data, index, arr);
      });

      this._nodeEnter(nodeEnter, nodes); // UPDATE


      var nodeUpdate = nodeEnter.merge(nodes);
      var nodeUpdateTransition = nodeUpdate.transition().duration(this.getDuration());
      nodeUpdate.classed("collapsed", function (data, index, arr) {
        if (!data.children && data._children) return true;else if (_this9.loadOnDemandSettings.isEnabled() && _this9.loadOnDemandSettings.hasChildren(data.data) && !data.children && !data._children) // If it does have children to load via AJAX
          return true;
        return false;
      }).classed("expanded", function (data, index, arr) {
        return data.children;
      }).classed("childless", function (data, index, arr) {
        return !data.children && !data._children;
      }).classed("selected", function (data, index, arr) {
        return data.selected;
      });

      this._nodeUpdate(nodeUpdate, nodeUpdateTransition, nodes); // Remove any exiting nodes


      var nodeExit = nodes.exit();
      var nodeExitTransition = nodeExit.transition().duration(this.getDuration());

      this._nodeExit(nodeExit, nodeExitTransition, nodes);

      return this;
    }
    /**
     * Updates the tree node links given
     * a D3 tree node.
     *
     * @param {object} nodeDataItem The D3 node data item.
     * @param {object[]} links Array of D3 link data items.
     * @returns {object} The tree object.
     */

  }, {
    key: "_updateLinks",
    value: function _updateLinks(nodeDataItem, links) {
      var _this10 = this;

      var linkPathGenerator = this._getLinkPathGenerator(); // Update the links...


      var link = this.getPanningContainer().selectAll("path.link").data(links, function (data) {
        return _this10.getId.call(_this10, data.data);
      }); // Enter any new links at the parent's previous position.

      var linkEnter = link.enter().insert("path", "g").classed("link", true);

      this._linkEnter(nodeDataItem, linkEnter, link, linkPathGenerator); // UPDATE


      var linkUpdate = linkEnter.merge(link);
      var linkUpdateTransition = linkUpdate.transition().duration(this.getDuration()); // Transition back to the parent element position

      this._linkUpdate(nodeDataItem, linkUpdate, linkUpdateTransition, link, linkPathGenerator); // Remove any exiting links


      var linkExit = link.exit();
      var linkExitTransition = linkExit.transition().duration(this.getDuration());

      this._linkExit(nodeDataItem, linkExit, linkExitTransition, link, linkPathGenerator); // Store the old positions for transition.


      this.getVisibleNodes().forEach(function (data) {
        data.x0 = data.x;
        data.y0 = data.y;
      });
      return this;
    }
    /**
     * Updates the tree given a D3 tree node.
     *
     * @param {object} nodeDataItem The D3 node data item.
     * @returns {object} The tree object.
     */

  }, {
    key: "update",
    value: function update(nodeDataItem) {
      var treeGenerator = this.getTreeGenerator(); // Assigns the x and y position for the nodes

      var treeData = treeGenerator(this.getRoot());
      this._visibleNodes = treeData.descendants();
      this._nodes = [this.getRoot()].concat(_toConsumableArray(recursiveGet(this.getRoot(), function (node) {
        return node._children;
      })));
      this._links = treeData.descendants().slice(1);

      this._updateNodes(nodeDataItem, this.getVisibleNodes())._updateLinks(nodeDataItem, this.getLinks());

      return this;
    }
    /**
     * Gets the unique ID for a given data item.
     * @callback getIdCallBack
     * @param {object} data Represents the single data item to extract the ID from.
     * @returns {*} The unique ID from the given data item.
     */

    /**
     * Gets the parent ID for a given data item.
     * @callback getParentIdCallBack
     * @param {object} data Represents the single data item to extract the parent ID from.
     * @returns {*} The parent ID from the given data item.
     */

    /**
     * Gets the children items for a given
     * data item.
     * @callback getChildrenCallBack
     * @param {object} data Represents the single data item to extract the children data items from.
     * @returns {object[]} The array of data items representing the children of the given data item.
     */

    /**
     * Event handler for the node click event.
     * @callback nodeClickCallBack
     * @param {object} nodeDataItem Node data item representing the clicked node.
     * @param {object} nodeDataItem.data The data item of the clicked node.
     * @param {number} index Index of the clicked item in the array of siblings.
     * @param {object[]} arr The array of sibling rendered SVG elements, inclusive of the node itself.
     * @returns {boolean} If returns false, it'll prevent propogation to focus/expand/collapse the node.
     */

  }]);

  return BaseTree;
}(); // Define option defaults using a class static property


BaseTree_BaseTree.defaults = {
  theme: 'default',
  allowPan: true,
  allowZoom: true,
  allowFocus: true,
  allowNodeCentering: true,
  minScale: 1,
  // Minimum zoom scaling
  maxScale: 2,
  // Maximum zoom scaling
  // You can increase the depth multiplication to get more depth,
  // i.e. increasing the distance between the parent node and child node
  nodeDepthMultiplier: 300,
  isFlatData: false,
  getId: null,
  getParentId: null,
  getChildren: null,
  widthWithoutMargin: 960,
  heightWithoutMargin: 800,
  margin: {
    top: 40,
    right: 20,
    bottom: 40,
    left: 100
  },
  duration: 750,
  events: {
    nodeClick: null
  },
  loadOnDemandSettings: {// Defaults are defined in the load-on-demand settings prototype
  },
  nodeSettings: {// Defaults are defined in the node settings prototype
  }
};
/* harmony default export */ var js_BaseTree = (BaseTree_BaseTree);
// CONCATENATED MODULE: ./src/js/BoxedNodeSettings.js
function BoxedNodeSettings_typeof(obj) { if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { BoxedNodeSettings_typeof = function _typeof(obj) { return typeof obj; }; } else { BoxedNodeSettings_typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return BoxedNodeSettings_typeof(obj); }

function BoxedNodeSettings_objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; var ownKeys = Object.keys(source); if (typeof Object.getOwnPropertySymbols === 'function') { ownKeys = ownKeys.concat(Object.getOwnPropertySymbols(source).filter(function (sym) { return Object.getOwnPropertyDescriptor(source, sym).enumerable; })); } ownKeys.forEach(function (key) { BoxedNodeSettings_defineProperty(target, key, source[key]); }); } return target; }

function BoxedNodeSettings_defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function BoxedNodeSettings_classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function BoxedNodeSettings_defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function BoxedNodeSettings_createClass(Constructor, protoProps, staticProps) { if (protoProps) BoxedNodeSettings_defineProperties(Constructor.prototype, protoProps); if (staticProps) BoxedNodeSettings_defineProperties(Constructor, staticProps); return Constructor; }

function _possibleConstructorReturn(self, call) { if (call && (BoxedNodeSettings_typeof(call) === "object" || typeof call === "function")) { return call; } return _assertThisInitialized(self); }

function _assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function _getPrototypeOf(o) { _getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return _getPrototypeOf(o); }

function _inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) _setPrototypeOf(subClass, superClass); }

function _setPrototypeOf(o, p) { _setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return _setPrototypeOf(o, p); }



var BoxedNodeSettings =
/*#__PURE__*/
function (_NodeSettings) {
  _inherits(BoxedNodeSettings, _NodeSettings);

  /**
   * @param {object} ownerObject The owner object.
   * @param {object} options The options object.
   * @param {number} [options.bodyBoxWidth=200] Body box width.
   * @param {number} [options.bodyBoxHeight=75] Body box height.
   * @param {object} [options.bodyBoxPadding] Body box padding object.
   * @param {number} [options.bodyBoxPadding.top=5] Body box padding top.
   * @param {number} [options.bodyBoxPadding.right=10] Body box padding right.
   * @param {number} [options.bodyBoxPadding.bottom=5] Body box padding bottom.
   * @param {number} [options.bodyBoxPadding.left=10] Body box padding left.
   * @param {number} [options.titleBoxWidth] Title box width.
   * @param {number} [options.titleBoxHeight=40] Title box height.
   * @param {object} [options.titleBoxPadding] Title box padding object.
   * @param {number} [options.titleBoxPadding.top=2] Title box padding top.
   * @param {number} [options.titleBoxPadding.right=5] Title box padding right.
   * @param {number} [options.titleBoxPadding.bottom=2] Title box padding bottom.
   * @param {number} [options.titleBoxPadding.left=5] Title box padding left.
   */
  function BoxedNodeSettings(ownerObject, options) {
    var _this;

    BoxedNodeSettings_classCallCheck(this, BoxedNodeSettings);

    _this = _possibleConstructorReturn(this, _getPrototypeOf(BoxedNodeSettings).call(this, ownerObject, options));

    var mergedOptions = BoxedNodeSettings_objectSpread({}, BoxedNodeSettings.defaults, options);

    _this._bodyBoxWidth = mergedOptions.bodyBoxWidth;
    _this._bodyBoxHeight = mergedOptions.bodyBoxHeight;
    _this._bodyBoxPadding = mergedOptions.bodyBoxPadding;
    _this._titleBoxWidth = mergedOptions.titleBoxWidth;
    _this._titleBoxHeight = mergedOptions.titleBoxHeight;
    _this._titleBoxPadding = mergedOptions.titleBoxPadding;
    return _this;
  }
  /**
   * Gets the body box width value.
   *
   * @returns {number} The body box width value.
   */


  BoxedNodeSettings_createClass(BoxedNodeSettings, [{
    key: "getBodyBoxWidth",
    value: function getBodyBoxWidth() {
      return this._bodyBoxWidth;
    }
    /**
     * Sets the body box width value.
     *
     * @param {number} width The body box width value.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setBodyBoxWidth",
    value: function setBodyBoxWidth(width) {
      this._bodyBoxWidth = width;
      return this;
    }
    /**
     * Gets the body box height value.
     *
     * @returns {number} The body box height value.
     */

  }, {
    key: "getBodyBoxHeight",
    value: function getBodyBoxHeight() {
      return this._bodyBoxHeight;
    }
    /**
     * Sets the body box height value.
     *
     * @param {number} height The body box height value.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setBodyBoxHeight",
    value: function setBodyBoxHeight(height) {
      this._bodyBoxHeight = height;
      return this;
    }
    /**
     * Sets the body box padding values.
     *
     * @param {object} newPadding The body box padding object value.
     * @param {number} newPadding.top The body box padding top value.
     * @param {number} newPadding.right The body box padding right value.
     * @param {number} newPadding.bottom The body box padding bottom value.
     * @param {number} newPadding.left The body box padding left value.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setBodyBoxPadding",
    value: function setBodyBoxPadding(newPadding) {
      this._bodyBoxPadding = newPadding;
      return this;
    }
    /**
     * Gets the body box padding values.
     *
     * @returns {object} The body box padding object.
     */

  }, {
    key: "getBodyBoxPadding",
    value: function getBodyBoxPadding() {
      return this._bodyBoxPadding;
    }
    /**
     * Gets the title box width value.
     *
     * @returns {number} The title box width value.
     */

  }, {
    key: "getTitleBoxWidth",
    value: function getTitleBoxWidth() {
      if (this._titleBoxWidth) return this._titleBoxWidth;else return this.getBodyBoxWidth() / 2;
    }
    /**
     * Sets the title box width value.
     *
     * @param {number} width The title box width value.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setTitleBoxWidth",
    value: function setTitleBoxWidth(width) {
      this._titleBoxWidth = width;
      return this;
    }
    /**
     * Gets the title box height value.
     *
     * @returns {number} The title box height value.
     */

  }, {
    key: "getTitleBoxHeight",
    value: function getTitleBoxHeight() {
      return this._titleBoxHeight;
    }
    /**
     * Sets the title box height value.
     *
     * @param {number} height The title box height value.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setTitleBoxHeight",
    value: function setTitleBoxHeight(height) {
      this._titleBoxHeight = height;
      return this;
    }
    /**
     * Gets the title box padding values.
     *
     * @returns {object} The title box padding object.
     */

  }, {
    key: "getTitleBoxPadding",
    value: function getTitleBoxPadding() {
      return this._titleBoxPadding;
    }
    /**
     * Sets the title box padding values.
     *
     * @param {object} newPadding The body box padding object value.
     * @param {number} newPadding.top The body box padding top value.
     * @param {number} newPadding.right The body box padding right value.
     * @param {number} newPadding.bottom The body box padding bottom value.
     * @param {number} newPadding.left The body box padding left value.
     * @returns {object} The node settings object.
     */

  }, {
    key: "setTitleBoxPadding",
    value: function setTitleBoxPadding(newPadding) {
      this._titleBoxPadding = newPadding;
      return this;
    }
  }]);

  return BoxedNodeSettings;
}(js_NodeSettings);

BoxedNodeSettings.defaults = {
  bodyBoxWidth: 150,
  bodyBoxHeight: 40,
  bodyBoxPadding: {
    top: 5,
    right: 10,
    bottom: 5,
    left: 10
  },
  titleBoxWidth: null,
  titleBoxHeight: 40,
  titleBoxPadding: {
    top: 2,
    right: 5,
    bottom: 2,
    left: 5
  }
};
/* harmony default export */ var js_BoxedNodeSettings = (BoxedNodeSettings);
// CONCATENATED MODULE: ./src/js/BoxedTree.js
function BoxedTree_typeof(obj) { if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { BoxedTree_typeof = function _typeof(obj) { return typeof obj; }; } else { BoxedTree_typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return BoxedTree_typeof(obj); }

function BoxedTree_objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; var ownKeys = Object.keys(source); if (typeof Object.getOwnPropertySymbols === 'function') { ownKeys = ownKeys.concat(Object.getOwnPropertySymbols(source).filter(function (sym) { return Object.getOwnPropertyDescriptor(source, sym).enumerable; })); } ownKeys.forEach(function (key) { BoxedTree_defineProperty(target, key, source[key]); }); } return target; }

function BoxedTree_defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function BoxedTree_classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function BoxedTree_defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function BoxedTree_createClass(Constructor, protoProps, staticProps) { if (protoProps) BoxedTree_defineProperties(Constructor.prototype, protoProps); if (staticProps) BoxedTree_defineProperties(Constructor, staticProps); return Constructor; }

function BoxedTree_possibleConstructorReturn(self, call) { if (call && (BoxedTree_typeof(call) === "object" || typeof call === "function")) { return call; } return BoxedTree_assertThisInitialized(self); }

function _get(target, property, receiver) { if (typeof Reflect !== "undefined" && Reflect.get) { _get = Reflect.get; } else { _get = function _get(target, property, receiver) { var base = _superPropBase(target, property); if (!base) return; var desc = Object.getOwnPropertyDescriptor(base, property); if (desc.get) { return desc.get.call(receiver); } return desc.value; }; } return _get(target, property, receiver || target); }

function _superPropBase(object, property) { while (!Object.prototype.hasOwnProperty.call(object, property)) { object = BoxedTree_getPrototypeOf(object); if (object === null) break; } return object; }

function BoxedTree_getPrototypeOf(o) { BoxedTree_getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return BoxedTree_getPrototypeOf(o); }

function BoxedTree_inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) BoxedTree_setPrototypeOf(subClass, superClass); }

function BoxedTree_setPrototypeOf(o, p) { BoxedTree_setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return BoxedTree_setPrototypeOf(o, p); }

function BoxedTree_assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }






var BoxedTree_BoxedTree =
/*#__PURE__*/
function (_BaseTree) {
  BoxedTree_inherits(BoxedTree, _BaseTree);

  /**
   * @param {object} options The options object.
   * @param {bodyDisplayTextAccessorCallBack} options.getBodyDisplayText Determines how to obtain the body text to display for a node corresponding to a data item.
   * @param {titleDisplayTextAccessorCallBack} options.getTitleDisplayText Determines how to obtain the title text to display for a node corresponding to a data item.
  */
  function BoxedTree(options) {
    var _this;

    BoxedTree_classCallCheck(this, BoxedTree);

    _this = BoxedTree_possibleConstructorReturn(this, BoxedTree_getPrototypeOf(BoxedTree).call(this, options));

    var mergedOptions = BoxedTree_objectSpread({}, js_BaseTree.defaults, BoxedTree.defaults, options);

    _this._getBodyDisplayText = mergedOptions.getBodyDisplayText;
    _this._getTitleDisplayText = mergedOptions.getTitleDisplayText;
    _this.nodeSettings = new js_BoxedNodeSettings(BoxedTree_assertThisInitialized(BoxedTree_assertThisInitialized(_this)), mergedOptions.nodeSettings);
    return _this;
  }
  /** @inheritdoc */


  BoxedTree_createClass(BoxedTree, [{
    key: "initialize",
    value: function initialize() {
      _get(BoxedTree_getPrototypeOf(BoxedTree.prototype), "initialize", this).call(this); // Create the svg, and set its dimensions


      this.getSvg().classed('boxed-tree', true);
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_nodeEnter",
    value: function _nodeEnter(nodeEnter, nodes) {
      var self = this; // Declare box dimensions

      var nodeBodyBoxWidth = self.nodeSettings.getBodyBoxWidth();
      var nodeBodyBoxHeight = self.nodeSettings.getBodyBoxHeight();
      var nodeBodyBoxPadding = self.nodeSettings.getBodyBoxPadding();
      var nodeTitleBoxWidth = self.nodeSettings.getTitleBoxWidth();
      var nodeTitleBoxHeight = self.nodeSettings.getTitleBoxHeight();
      var nodeTitleBoxPadding = self.nodeSettings.getTitleBoxPadding();
      /* Add Body Rectangle and Text for Node */

      var bodyGroups = nodeEnter.append("g").classed("body-group", true);
      bodyGroups.append("rect").classed("body-box", true).attr("width", 1e-6).attr("height", 1e-6);
      bodyGroups.each(function (data, index, arr) {
        var element = this;
        var selection = CustomD3.select(element);
        var singledOutData = [];
        singledOutData.push(data);
        var recalculatedPaddingTop = nodeBodyBoxPadding.top;

        if (self.getTitleDisplayText.call(self, data)) {
          recalculatedPaddingTop += nodeTitleBoxHeight / 2;
        } // D3Plus Textbox with resizing capability


        var d3PlusBodyTextBox = new src_TextBox().select(element) // Sets the D3Plus code to append to the specified DOM element.
        .data(singledOutData).text(function (data, index, arr) {
          return self.getBodyDisplayText.call(self, data);
        }).textAnchor("middle").verticalAlign("middle").fontSize(10) // in pixels
        .x(nodeBodyBoxPadding.left).y(recalculatedPaddingTop - nodeBodyBoxHeight / 2).width(nodeBodyBoxWidth - nodeBodyBoxPadding.left - nodeBodyBoxPadding.right).height(nodeBodyBoxHeight - recalculatedPaddingTop - nodeBodyBoxPadding.bottom).ellipsis(function (text, line) {
          // If text was cut-off, add tooltip
          selection.append("title").text(self.getBodyDisplayText(data));
          return text.replace(/\.|,$/g, "") + "...";
        }).render();
      });
      /* Add Title Rectangle and Text for Node */

      var titleGroups = nodeEnter.append("g").classed("title-group", true).attr("transform", "translate(" + -nodeTitleBoxWidth / 3 + ", " + (-nodeTitleBoxHeight / 2 - nodeBodyBoxHeight / 2) + ")");
      titleGroups.each(function (data, index, arr) {
        if (!self.getTitleDisplayText.call(self, data)) return;
        var element = this;
        var selection = CustomD3.select(element);
        var singledOutData = [];
        singledOutData.push(data);
        selection.append("rect").classed("title-box", true).attr("width", nodeTitleBoxWidth).attr("height", nodeTitleBoxHeight); // D3Plus Textbox with resizing capability

        var d3PlusTitleTextBox = new src_TextBox().select(element) // Sets the D3Plus code to append to the DOM element.
        .data(singledOutData).text(function (data, index, arr) {
          return self.getTitleDisplayText.call(self, data);
        }).textAnchor("middle").verticalAlign("middle").x(nodeTitleBoxPadding.left).y(nodeTitleBoxPadding.top).fontWeight(700).fontMin(6).fontMax(16).fontResize(true) // Resizes the text to fit the content
        .width(nodeTitleBoxWidth - nodeTitleBoxPadding.left - nodeTitleBoxPadding.right).height(nodeTitleBoxHeight - nodeTitleBoxPadding.top - nodeTitleBoxPadding.bottom).render();
      });
      return self;
    }
    /** @inheritdoc */

  }, {
    key: "_nodeUpdate",
    value: function _nodeUpdate(nodeUpdate, nodeUpdateTransition, nodes) {
      // Transition to the proper position for the node
      // Translating while inverting X/Y to
      // make tree direction from left to right,
      // instead of the typical top-to-down tree
      nodeUpdateTransition.attr("transform", function (data, index, arr) {
        return "translate(" + data.y + "," + data.x + ")";
      });
      var nodeBodyBoxWidth = this.nodeSettings.getBodyBoxWidth();
      var nodeBodyBoxHeight = this.nodeSettings.getBodyBoxHeight(); // Update the node attributes and style

      nodeUpdate.select(".node .body-group .body-box").attr("y", -(nodeBodyBoxHeight / 2)).attr("width", nodeBodyBoxWidth).attr("height", nodeBodyBoxHeight);
      nodeUpdate.select(".d3plus-textBox").style("fill-opacity", 1);
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_nodeExit",
    value: function _nodeExit(nodeExit, nodeExitTransition, nodes) {
      var nodeBodyBoxWidth = this.nodeSettings.getBodyBoxWidth();
      var nodeBodyBoxHeight = this.nodeSettings.getBodyBoxHeight();
      nodeExitTransition.attr("transform", function (data, index, arr) {
        var highestCollapsingParent = data.parent;

        while (highestCollapsingParent.parent && !highestCollapsingParent.parent.children) {
          highestCollapsingParent = highestCollapsingParent.parent;
        } // Translating while inverting X/Y to
        // make tree direction from left to right,
        // instead of the typical top-to-down tree


        return "translate(" + (highestCollapsingParent.y + nodeBodyBoxWidth) + "," + (highestCollapsingParent.x + nodeBodyBoxHeight / 2) + ")";
      }).remove(); // On exit animate out

      nodeExitTransition.select(".node .body-group rect").attr("width", 1e-6).attr("height", 1e-6);
      nodeExitTransition.select(".node .body-group .d3plus-textBox").style("fill-opacity", 1e-6).attr("transform", function (data, index, arr) {
        return "translate(0," + -nodeBodyBoxHeight / 2 + ")";
      }).selectAll("text").style("font-size", 0).attr("y", 0).attr("x", 0);
      nodeExitTransition.select(".node .title-group").attr("transform", "translate(0, " + -nodeBodyBoxHeight / 2 + ")");
      nodeExitTransition.select(".node .title-group rect").attr("width", 1e-6).attr("height", 1e-6);
      nodeExitTransition.select(".node .title-group .d3plus-textBox").style("fill-opacity", 1e-6).attr("transform", "translate(0,0)").selectAll("text").style("font-size", 0).attr("y", 0).attr("x", 0); // On exit reduce the opacity of text labels

      nodeExitTransition.select(".d3plus-textBox").style("fill-opacity", 1e-6);
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_getNodeSize",
    value: function _getNodeSize() {
      return [this.nodeSettings.getBodyBoxHeight() + this.nodeSettings.getVerticalSpacing(), this.nodeSettings.getBodyBoxWidth() + this.nodeSettings.getHorizontalSpacing()];
    }
    /** @inheritdoc */

  }, {
    key: "_linkEnter",
    value: function _linkEnter(source, linkEnter, links, linkPathGenerator) {
      linkEnter.attr("d", function (data, index, arr) {
        var sourceCoordinate = {
          x: source.x0,
          y: source.y0
        };
        var coordinatesObject = {
          source: sourceCoordinate,
          target: sourceCoordinate
        };
        return linkPathGenerator(coordinatesObject);
      });
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_linkUpdate",
    value: function _linkUpdate(source, linkUpdate, linkUpdateTransition, links, linkPathGenerator) {
      linkUpdateTransition.attr("d", function (data, index, arr) {
        var sourceCoordinate = data;
        var targetCoordinate = data.parent;
        var coordinatesObject = {
          source: sourceCoordinate,
          target: targetCoordinate
        };
        return linkPathGenerator(coordinatesObject);
      });
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_linkExit",
    value: function _linkExit(source, linkExit, linkExitTransition, links, linkPathGenerator) {
      var nodeBodyBoxWidth = this.nodeSettings.getBodyBoxWidth();
      linkExitTransition.attr("d", function (data, index, arr) {
        var highestCollapsingParent = data.parent;

        while (highestCollapsingParent.parent && !highestCollapsingParent.parent.children) {
          highestCollapsingParent = highestCollapsingParent.parent;
        }

        var sourceCoordinate = {
          x: highestCollapsingParent.x,
          y: highestCollapsingParent.y + nodeBodyBoxWidth
        };
        var targetCoordinate = {
          x: highestCollapsingParent.x,
          y: highestCollapsingParent.y
        };
        var coordinatesObject = {
          source: sourceCoordinate,
          target: targetCoordinate
        };
        return linkPathGenerator(coordinatesObject);
      });
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_getLinkPathGenerator",
    value: function _getLinkPathGenerator() {
      // Declare box dimensions
      var nodeBodyBoxWidth = this.nodeSettings.getBodyBoxWidth();
      return CustomD3.linkHorizontal() // We specify arrow functions that returns
      // an array specifying how to get the
      // the x/y cordinates from the object,
      // in the format of [x, y], the default
      // format for the link generator to
      // generate the path
      // Inverts the X/Y coordinates to draw links for a
      // tree starting from left to right,
      // instead of the typical top-to-down tree
      .source(function (data) {
        return [data.source.y, data.source.x];
      }).target(function (data) {
        return [data.target.y + nodeBodyBoxWidth, data.target.x];
      });
    }
    /** @inheritdoc */

  }, {
    key: "validateSettings",
    value: function validateSettings() {
      _get(BoxedTree_getPrototypeOf(BoxedTree.prototype), "validateSettings", this).call(this);

      if (!this._getBodyDisplayText) throw "Need to define the getBodyDisplayText function as part of the options";
      return this;
    }
    /**
     * Sets the body display text accessor,
     * used to get the body display text
     * for the nodes.
     *
     * @param {bodyDisplayTextAccessorCallBack} newBodyDisplayTextAccessor
     */

  }, {
    key: "setBodyDisplayTextAccessor",
    value: function setBodyDisplayTextAccessor(newBodyDisplayTextAccessor) {
      this._getBodyDisplayText = newBodyDisplayTextAccessor;
      return this;
    }
    /**
     * Gets the body display text for a given data item.
     *
     * @param {object} nodeDataItem The data item to get the body display text from.
     * @returns {string} The body display text to render for the node.
     */

  }, {
    key: "getBodyDisplayText",
    value: function getBodyDisplayText(nodeDataItem) {
      // Note that data in this context refers to D3 Tree data, not the original item data
      // To Access the original item data, use the ".data" property
      return this._getBodyDisplayText(nodeDataItem.data);
    }
    /**
     * Sets the title display text accessor,
     * used to get the title display text
     * for the nodes.
     *
     * @param {titleDisplayTextAccessorCallBack} newTitleDisplayTextAccessor
     */

  }, {
    key: "setTitleDisplayTextAccessor",
    value: function setTitleDisplayTextAccessor(newTitleDisplayTextAccessor) {
      this._getTitleDisplayText = newTitleDisplayTextAccessor;
      return this;
    }
    /**
     * Gets the title display text for a given data item.
     *
     * @param {object} nodeDataItem The D3 node data item to get the title display text from.
     * @returns {string} The title display text to render for the node.
     */

  }, {
    key: "getTitleDisplayText",
    value: function getTitleDisplayText(nodeDataItem) {
      // Note that data in this context refers to D3 Tree data, not the original item data
      // To Access the original item data, use the ".data" property
      return this._getTitleDisplayText(nodeDataItem.data);
    }
    /**
     * Determines how to obtain the body text
     * to display for a node corresponding
     * to a data item.
     *
     * @callback bodyDisplayTextAccessorCallBack
     * @param {object} data The data item to get the body display text from.
     * @returns {string} The body display text to render for the node.
     */

    /**
     * Determines how to obtain the title text
     * to display for a node corresponding
     * to a data item.
     *
     * @callback titleDisplayTextAccessorCallBack
     * @param {object} data The data item to get the title display text from.
     * @returns {string} The title display text to render for the node.
     */

  }]);

  return BoxedTree;
}(js_BaseTree);

BoxedTree_BoxedTree.defaults = {
  getBodyDisplayText: null,
  getTitleDisplayText: function getTitleDisplayText(dataItem) {
    return null;
  }
};
/* harmony default export */ var js_BoxedTree = (BoxedTree_BoxedTree);
// CONCATENATED MODULE: ./src/js/CircleNodeSettings.js
function CircleNodeSettings_typeof(obj) { if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { CircleNodeSettings_typeof = function _typeof(obj) { return typeof obj; }; } else { CircleNodeSettings_typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return CircleNodeSettings_typeof(obj); }

function CircleNodeSettings_classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function CircleNodeSettings_possibleConstructorReturn(self, call) { if (call && (CircleNodeSettings_typeof(call) === "object" || typeof call === "function")) { return call; } return CircleNodeSettings_assertThisInitialized(self); }

function CircleNodeSettings_assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }

function CircleNodeSettings_getPrototypeOf(o) { CircleNodeSettings_getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return CircleNodeSettings_getPrototypeOf(o); }

function CircleNodeSettings_inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) CircleNodeSettings_setPrototypeOf(subClass, superClass); }

function CircleNodeSettings_setPrototypeOf(o, p) { CircleNodeSettings_setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return CircleNodeSettings_setPrototypeOf(o, p); }



var CircleNodeSettings =
/*#__PURE__*/
function (_NodeSettings) {
  CircleNodeSettings_inherits(CircleNodeSettings, _NodeSettings);

  function CircleNodeSettings() {
    CircleNodeSettings_classCallCheck(this, CircleNodeSettings);

    return CircleNodeSettings_possibleConstructorReturn(this, CircleNodeSettings_getPrototypeOf(CircleNodeSettings).apply(this, arguments));
  }

  return CircleNodeSettings;
}(js_NodeSettings);

/* harmony default export */ var js_CircleNodeSettings = (CircleNodeSettings);
// CONCATENATED MODULE: ./src/js/CircleTree.js
function CircleTree_typeof(obj) { if (typeof Symbol === "function" && typeof Symbol.iterator === "symbol") { CircleTree_typeof = function _typeof(obj) { return typeof obj; }; } else { CircleTree_typeof = function _typeof(obj) { return obj && typeof Symbol === "function" && obj.constructor === Symbol && obj !== Symbol.prototype ? "symbol" : typeof obj; }; } return CircleTree_typeof(obj); }

function CircleTree_objectSpread(target) { for (var i = 1; i < arguments.length; i++) { var source = arguments[i] != null ? arguments[i] : {}; var ownKeys = Object.keys(source); if (typeof Object.getOwnPropertySymbols === 'function') { ownKeys = ownKeys.concat(Object.getOwnPropertySymbols(source).filter(function (sym) { return Object.getOwnPropertyDescriptor(source, sym).enumerable; })); } ownKeys.forEach(function (key) { CircleTree_defineProperty(target, key, source[key]); }); } return target; }

function CircleTree_defineProperty(obj, key, value) { if (key in obj) { Object.defineProperty(obj, key, { value: value, enumerable: true, configurable: true, writable: true }); } else { obj[key] = value; } return obj; }

function CircleTree_classCallCheck(instance, Constructor) { if (!(instance instanceof Constructor)) { throw new TypeError("Cannot call a class as a function"); } }

function CircleTree_defineProperties(target, props) { for (var i = 0; i < props.length; i++) { var descriptor = props[i]; descriptor.enumerable = descriptor.enumerable || false; descriptor.configurable = true; if ("value" in descriptor) descriptor.writable = true; Object.defineProperty(target, descriptor.key, descriptor); } }

function CircleTree_createClass(Constructor, protoProps, staticProps) { if (protoProps) CircleTree_defineProperties(Constructor.prototype, protoProps); if (staticProps) CircleTree_defineProperties(Constructor, staticProps); return Constructor; }

function CircleTree_possibleConstructorReturn(self, call) { if (call && (CircleTree_typeof(call) === "object" || typeof call === "function")) { return call; } return CircleTree_assertThisInitialized(self); }

function CircleTree_get(target, property, receiver) { if (typeof Reflect !== "undefined" && Reflect.get) { CircleTree_get = Reflect.get; } else { CircleTree_get = function _get(target, property, receiver) { var base = CircleTree_superPropBase(target, property); if (!base) return; var desc = Object.getOwnPropertyDescriptor(base, property); if (desc.get) { return desc.get.call(receiver); } return desc.value; }; } return CircleTree_get(target, property, receiver || target); }

function CircleTree_superPropBase(object, property) { while (!Object.prototype.hasOwnProperty.call(object, property)) { object = CircleTree_getPrototypeOf(object); if (object === null) break; } return object; }

function CircleTree_getPrototypeOf(o) { CircleTree_getPrototypeOf = Object.setPrototypeOf ? Object.getPrototypeOf : function _getPrototypeOf(o) { return o.__proto__ || Object.getPrototypeOf(o); }; return CircleTree_getPrototypeOf(o); }

function CircleTree_inherits(subClass, superClass) { if (typeof superClass !== "function" && superClass !== null) { throw new TypeError("Super expression must either be null or a function"); } subClass.prototype = Object.create(superClass && superClass.prototype, { constructor: { value: subClass, writable: true, configurable: true } }); if (superClass) CircleTree_setPrototypeOf(subClass, superClass); }

function CircleTree_setPrototypeOf(o, p) { CircleTree_setPrototypeOf = Object.setPrototypeOf || function _setPrototypeOf(o, p) { o.__proto__ = p; return o; }; return CircleTree_setPrototypeOf(o, p); }

function CircleTree_assertThisInitialized(self) { if (self === void 0) { throw new ReferenceError("this hasn't been initialised - super() hasn't been called"); } return self; }





var CircleTree_CircleTree =
/*#__PURE__*/
function (_BaseTree) {
  CircleTree_inherits(CircleTree, _BaseTree);

  /**
   * @param {object} [options] The options object.
   * @param {displayTextAccessorCallBack} [options.getDisplayText] Determines how to obtain the text to display for a node corresponding to a data item.
   */
  function CircleTree(options) {
    var _this;

    CircleTree_classCallCheck(this, CircleTree);

    _this = CircleTree_possibleConstructorReturn(this, CircleTree_getPrototypeOf(CircleTree).call(this, options));

    var mergedOptions = CircleTree_objectSpread({}, js_BaseTree.defaults, CircleTree.defaults, options);

    _this._getDisplayText = mergedOptions.getDisplayText;
    _this.nodeSettings = new js_CircleNodeSettings(CircleTree_assertThisInitialized(CircleTree_assertThisInitialized(_this)), mergedOptions.nodeSettings);
    return _this;
  }
  /** @inheritdoc */


  CircleTree_createClass(CircleTree, [{
    key: "initialize",
    value: function initialize() {
      // Create the svg, and set its dimensions
      CircleTree_get(CircleTree_getPrototypeOf(CircleTree.prototype), "initialize", this).call(this);

      this.getSvg().classed('circle-tree', true);
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_nodeEnter",
    value: function _nodeEnter(nodeEnter, nodes) {
      var _this2 = this;

      // Add Circle for the nodes
      nodeEnter.append("circle").attr("r", 1e-6); // Add labels for the nodes

      nodeEnter.append("text").text(function (data, index, arr) {
        return _this2.getDisplayText.call(_this2, data);
      });
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_nodeUpdate",
    value: function _nodeUpdate(nodeUpdate, nodeUpdateTransition, nodes) {
      nodeUpdate.classed('middle', function (data, index, arr) {
        var isMiddleChild = false;

        if (data.parent && data.parent.children.length % 2 !== 0) {
          var siblings = data.parent.children;
          var indexOfSiblings = siblings.indexOf(data);
          if (indexOfSiblings === Math.floor(siblings.length / 2)) isMiddleChild = true;
        }

        return isMiddleChild;
      }); // Transition to the proper position for the node

      nodeUpdate.transition().duration(this.getDuration()) // Translating while inverting X/Y to
      // make tree direction from left to right,
      // instead of the typical top-to-down tree
      .attr("transform", function (data, index, arr) {
        return "translate(" + data.y + "," + data.x + ")";
      });
      nodeUpdate.select("text").style("fill-opacity", 1);
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_nodeExit",
    value: function _nodeExit(nodeExit, nodeExitTransition, nodes) {
      // Remove any exiting nodes
      nodeExitTransition.attr("transform", function (data, index, arr) {
        var highestCollapsingParent = data.parent;

        while (highestCollapsingParent.parent && !highestCollapsingParent.parent.children) {
          highestCollapsingParent = highestCollapsingParent.parent;
        } // Translating while inverting X/Y to
        // make tree direction from left to right,
        // instead of the typical top-to-down tree


        return "translate(" + highestCollapsingParent.y + "," + highestCollapsingParent.x + ")";
      }).remove(); // On exit reduce the node circles size to 0

      nodeExitTransition.select("circle").attr("r", 1e-6); // On exit reduce the opacity of text labels

      nodeExitTransition.select("text").style("fill-opacity", 1e-6);
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_getNodeSize",
    value: function _getNodeSize() {
      return [this.nodeSettings.getVerticalSpacing(), this.nodeSettings.getHorizontalSpacing()];
    }
    /** @inheritdoc */

  }, {
    key: "_linkEnter",
    value: function _linkEnter(source, linkEnter, links, linkPathGenerator) {
      linkEnter.attr("d", function (data, index, arr) {
        var sourceCoordinate = {
          x: source.x0,
          y: source.y0
        };
        var coordinatesObject = {
          source: sourceCoordinate,
          target: sourceCoordinate
        };
        return linkPathGenerator(coordinatesObject);
      });
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_linkUpdate",
    value: function _linkUpdate(source, linkUpdate, linkUpdateTransition, links, linkPathGenerator) {
      linkUpdateTransition.attr("d", function (data, index, arr) {
        var sourceCoordinate = data;
        var targetCoordinate = data.parent;
        var coordinatesObject = {
          source: sourceCoordinate,
          target: targetCoordinate
        };
        return linkPathGenerator(coordinatesObject);
      });
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_linkExit",
    value: function _linkExit(source, linkExit, linkExitTransition, links, linkPathGenerator) {
      linkExitTransition.attr("d", function (data, index, arr) {
        var highestCollapsingParent = data.parent;

        while (highestCollapsingParent.parent && !highestCollapsingParent.parent.children) {
          highestCollapsingParent = highestCollapsingParent.parent;
        }

        var sourceCoordinate = {
          x: highestCollapsingParent.x,
          y: highestCollapsingParent.y
        };
        var targetCoordinate = {
          x: highestCollapsingParent.x,
          y: highestCollapsingParent.y
        };
        var coordinatesObject = {
          source: sourceCoordinate,
          target: targetCoordinate
        };
        return linkPathGenerator(coordinatesObject);
      });
      return this;
    }
    /** @inheritdoc */

  }, {
    key: "_getLinkPathGenerator",
    value: function _getLinkPathGenerator() {
      return CustomD3.linkHorizontal() // We specify arrow functions that returns
      // an array specifying how to get the
      // the x/y cordinates from the object,
      // in the format of [x, y], the default
      // format for the link generator to
      // generate the path
      // Inverts the X/Y coordinates to draw links for a
      // tree starting from left to right,
      // instead of the typical top-to-down tree
      .source(function (data) {
        return [data.source.y, data.source.x];
      }).target(function (data) {
        return [data.target.y, data.target.x];
      });
    }
    /** @inheritdoc */

  }, {
    key: "validateSettings",
    value: function validateSettings() {
      CircleTree_get(CircleTree_getPrototypeOf(CircleTree.prototype), "validateSettings", this).call(this);

      if (!this.getDisplayText) throw "Need to define the getDisplayText function as part of the options";
      return this;
    }
    /**
     * Sets the display text accessor,
     * used to get the display text
     * for the nodes.
     *
     * @param {displayTextAccessorCallBack} newDisplayTextAccessor
     */

  }, {
    key: "setDisplayTextAccessor",
    value: function setDisplayTextAccessor(newDisplayTextAccessor) {
      this._getDisplayText = newDisplayTextAccessor;
      return this;
    }
    /**
     * Gets the display text for a given data item.
     *
     * @param {object} nodeDataItem The data item to get the display text from.
     * @returns {string} The display text to render for the node.
     */

  }, {
    key: "getDisplayText",
    value: function getDisplayText(nodeDataItem) {
      // Note that data in this context refers to D3 Tree data, not the original item data
      // To Access the original item data, use the ".data" property
      return this._getDisplayText(nodeDataItem.data);
    }
    /**
     * Determines how to obtain the text
     * to display for a node corresponding
     * to a data item.
     *
     * @callback displayTextAccessorCallBack
     * @param {object} data The data item to get the display text from.
     * @returns {string} The display text to render for the node.
     */

  }]);

  return CircleTree;
}(js_BaseTree);

CircleTree_CircleTree.defaults = {
  getDisplayText: function getDisplayText(nodeDataItem) {
    return null;
  }
};
/* harmony default export */ var js_CircleTree = (CircleTree_CircleTree);
// CONCATENATED MODULE: ./src/index.js


/* harmony default export */ var src = __webpack_exports__["default"] = ({
  boxedTree: js_BoxedTree,
  circleTree: js_CircleTree
});

/***/ })
/******/ ])["default"];
});
