//#region \0rolldown/runtime.js
var e = Object.create, t = Object.defineProperty, n = Object.getOwnPropertyDescriptor, r = Object.getOwnPropertyNames, i = Object.getPrototypeOf, a = Object.prototype.hasOwnProperty, o = (e, t) => () => (t || (e((t = { exports: {} }).exports, t), e = null), t.exports), s = (e, i, o, s) => {
	if (i && typeof i == "object" || typeof i == "function") for (var c = r(i), l = 0, u = c.length, d; l < u; l++) d = c[l], !a.call(e, d) && d !== o && t(e, d, {
		get: ((e) => i[e]).bind(null, d),
		enumerable: !(s = n(i, d)) || s.enumerable
	});
	return e;
}, c = (n, r, a) => (a = n == null ? {} : e(i(n)), s(r || !n || !n.__esModule ? t(a, "default", {
	value: n,
	enumerable: !0
}) : a, n)), l = /* @__PURE__ */ o(((e) => {
	var t = Symbol.for("react.element"), n = Symbol.for("react.portal"), r = Symbol.for("react.fragment"), i = Symbol.for("react.strict_mode"), a = Symbol.for("react.profiler"), o = Symbol.for("react.provider"), s = Symbol.for("react.context"), c = Symbol.for("react.forward_ref"), l = Symbol.for("react.suspense"), u = Symbol.for("react.memo"), d = Symbol.for("react.lazy"), f = Symbol.iterator;
	function p(e) {
		return typeof e != "object" || !e ? null : (e = f && e[f] || e["@@iterator"], typeof e == "function" ? e : null);
	}
	var m = {
		isMounted: function() {
			return !1;
		},
		enqueueForceUpdate: function() {},
		enqueueReplaceState: function() {},
		enqueueSetState: function() {}
	}, h = Object.assign, g = {};
	function _(e, t, n) {
		this.props = e, this.context = t, this.refs = g, this.updater = n || m;
	}
	_.prototype.isReactComponent = {}, _.prototype.setState = function(e, t) {
		if (typeof e != "object" && typeof e != "function" && e != null) throw Error("setState(...): takes an object of state variables to update or a function which returns an object of state variables.");
		this.updater.enqueueSetState(this, e, t, "setState");
	}, _.prototype.forceUpdate = function(e) {
		this.updater.enqueueForceUpdate(this, e, "forceUpdate");
	};
	function v() {}
	v.prototype = _.prototype;
	function y(e, t, n) {
		this.props = e, this.context = t, this.refs = g, this.updater = n || m;
	}
	var b = y.prototype = new v();
	b.constructor = y, h(b, _.prototype), b.isPureReactComponent = !0;
	var x = Array.isArray, S = Object.prototype.hasOwnProperty, C = { current: null }, w = {
		key: !0,
		ref: !0,
		__self: !0,
		__source: !0
	};
	function T(e, n, r) {
		var i, a = {}, o = null, s = null;
		if (n != null) for (i in n.ref !== void 0 && (s = n.ref), n.key !== void 0 && (o = "" + n.key), n) S.call(n, i) && !w.hasOwnProperty(i) && (a[i] = n[i]);
		var c = arguments.length - 2;
		if (c === 1) a.children = r;
		else if (1 < c) {
			for (var l = Array(c), u = 0; u < c; u++) l[u] = arguments[u + 2];
			a.children = l;
		}
		if (e && e.defaultProps) for (i in c = e.defaultProps, c) a[i] === void 0 && (a[i] = c[i]);
		return {
			$$typeof: t,
			type: e,
			key: o,
			ref: s,
			props: a,
			_owner: C.current
		};
	}
	function E(e, n) {
		return {
			$$typeof: t,
			type: e.type,
			key: n,
			ref: e.ref,
			props: e.props,
			_owner: e._owner
		};
	}
	function D(e) {
		return typeof e == "object" && !!e && e.$$typeof === t;
	}
	function O(e) {
		var t = {
			"=": "=0",
			":": "=2"
		};
		return "$" + e.replace(/[=:]/g, function(e) {
			return t[e];
		});
	}
	var k = /\/+/g;
	function A(e, t) {
		return typeof e == "object" && e && e.key != null ? O("" + e.key) : t.toString(36);
	}
	function j(e, r, i, a, o) {
		var s = typeof e;
		(s === "undefined" || s === "boolean") && (e = null);
		var c = !1;
		if (e === null) c = !0;
		else switch (s) {
			case "string":
			case "number":
				c = !0;
				break;
			case "object": switch (e.$$typeof) {
				case t:
				case n: c = !0;
			}
		}
		if (c) return c = e, o = o(c), e = a === "" ? "." + A(c, 0) : a, x(o) ? (i = "", e != null && (i = e.replace(k, "$&/") + "/"), j(o, r, i, "", function(e) {
			return e;
		})) : o != null && (D(o) && (o = E(o, i + (!o.key || c && c.key === o.key ? "" : ("" + o.key).replace(k, "$&/") + "/") + e)), r.push(o)), 1;
		if (c = 0, a = a === "" ? "." : a + ":", x(e)) for (var l = 0; l < e.length; l++) {
			s = e[l];
			var u = a + A(s, l);
			c += j(s, r, i, u, o);
		}
		else if (u = p(e), typeof u == "function") for (e = u.call(e), l = 0; !(s = e.next()).done;) s = s.value, u = a + A(s, l++), c += j(s, r, i, u, o);
		else if (s === "object") throw r = String(e), Error("Objects are not valid as a React child (found: " + (r === "[object Object]" ? "object with keys {" + Object.keys(e).join(", ") + "}" : r) + "). If you meant to render a collection of children, use an array instead.");
		return c;
	}
	function M(e, t, n) {
		if (e == null) return e;
		var r = [], i = 0;
		return j(e, r, "", "", function(e) {
			return t.call(n, e, i++);
		}), r;
	}
	function N(e) {
		if (e._status === -1) {
			var t = e._result;
			t = t(), t.then(function(t) {
				(e._status === 0 || e._status === -1) && (e._status = 1, e._result = t);
			}, function(t) {
				(e._status === 0 || e._status === -1) && (e._status = 2, e._result = t);
			}), e._status === -1 && (e._status = 0, e._result = t);
		}
		if (e._status === 1) return e._result.default;
		throw e._result;
	}
	var P = { current: null }, F = { transition: null }, I = {
		ReactCurrentDispatcher: P,
		ReactCurrentBatchConfig: F,
		ReactCurrentOwner: C
	};
	function ee() {
		throw Error("act(...) is not supported in production builds of React.");
	}
	e.Children = {
		map: M,
		forEach: function(e, t, n) {
			M(e, function() {
				t.apply(this, arguments);
			}, n);
		},
		count: function(e) {
			var t = 0;
			return M(e, function() {
				t++;
			}), t;
		},
		toArray: function(e) {
			return M(e, function(e) {
				return e;
			}) || [];
		},
		only: function(e) {
			if (!D(e)) throw Error("React.Children.only expected to receive a single React element child.");
			return e;
		}
	}, e.Component = _, e.Fragment = r, e.Profiler = a, e.PureComponent = y, e.StrictMode = i, e.Suspense = l, e.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = I, e.act = ee, e.cloneElement = function(e, n, r) {
		if (e == null) throw Error("React.cloneElement(...): The argument must be a React element, but you passed " + e + ".");
		var i = h({}, e.props), a = e.key, o = e.ref, s = e._owner;
		if (n != null) {
			if (n.ref !== void 0 && (o = n.ref, s = C.current), n.key !== void 0 && (a = "" + n.key), e.type && e.type.defaultProps) var c = e.type.defaultProps;
			for (l in n) S.call(n, l) && !w.hasOwnProperty(l) && (i[l] = n[l] === void 0 && c !== void 0 ? c[l] : n[l]);
		}
		var l = arguments.length - 2;
		if (l === 1) i.children = r;
		else if (1 < l) {
			c = Array(l);
			for (var u = 0; u < l; u++) c[u] = arguments[u + 2];
			i.children = c;
		}
		return {
			$$typeof: t,
			type: e.type,
			key: a,
			ref: o,
			props: i,
			_owner: s
		};
	}, e.createContext = function(e) {
		return e = {
			$$typeof: s,
			_currentValue: e,
			_currentValue2: e,
			_threadCount: 0,
			Provider: null,
			Consumer: null,
			_defaultValue: null,
			_globalName: null
		}, e.Provider = {
			$$typeof: o,
			_context: e
		}, e.Consumer = e;
	}, e.createElement = T, e.createFactory = function(e) {
		var t = T.bind(null, e);
		return t.type = e, t;
	}, e.createRef = function() {
		return { current: null };
	}, e.forwardRef = function(e) {
		return {
			$$typeof: c,
			render: e
		};
	}, e.isValidElement = D, e.lazy = function(e) {
		return {
			$$typeof: d,
			_payload: {
				_status: -1,
				_result: e
			},
			_init: N
		};
	}, e.memo = function(e, t) {
		return {
			$$typeof: u,
			type: e,
			compare: t === void 0 ? null : t
		};
	}, e.startTransition = function(e) {
		var t = F.transition;
		F.transition = {};
		try {
			e();
		} finally {
			F.transition = t;
		}
	}, e.unstable_act = ee, e.useCallback = function(e, t) {
		return P.current.useCallback(e, t);
	}, e.useContext = function(e) {
		return P.current.useContext(e);
	}, e.useDebugValue = function() {}, e.useDeferredValue = function(e) {
		return P.current.useDeferredValue(e);
	}, e.useEffect = function(e, t) {
		return P.current.useEffect(e, t);
	}, e.useId = function() {
		return P.current.useId();
	}, e.useImperativeHandle = function(e, t, n) {
		return P.current.useImperativeHandle(e, t, n);
	}, e.useInsertionEffect = function(e, t) {
		return P.current.useInsertionEffect(e, t);
	}, e.useLayoutEffect = function(e, t) {
		return P.current.useLayoutEffect(e, t);
	}, e.useMemo = function(e, t) {
		return P.current.useMemo(e, t);
	}, e.useReducer = function(e, t, n) {
		return P.current.useReducer(e, t, n);
	}, e.useRef = function(e) {
		return P.current.useRef(e);
	}, e.useState = function(e) {
		return P.current.useState(e);
	}, e.useSyncExternalStore = function(e, t, n) {
		return P.current.useSyncExternalStore(e, t, n);
	}, e.useTransition = function() {
		return P.current.useTransition();
	}, e.version = "18.3.1";
})), u = /* @__PURE__ */ o(((e, t) => {
	t.exports = l();
})), d = /* @__PURE__ */ o(((e) => {
	function t(e, t) {
		var n = e.length;
		e.push(t);
		a: for (; 0 < n;) {
			var r = n - 1 >>> 1, a = e[r];
			if (0 < i(a, t)) e[r] = t, e[n] = a, n = r;
			else break a;
		}
	}
	function n(e) {
		return e.length === 0 ? null : e[0];
	}
	function r(e) {
		if (e.length === 0) return null;
		var t = e[0], n = e.pop();
		if (n !== t) {
			e[0] = n;
			a: for (var r = 0, a = e.length, o = a >>> 1; r < o;) {
				var s = 2 * (r + 1) - 1, c = e[s], l = s + 1, u = e[l];
				if (0 > i(c, n)) l < a && 0 > i(u, c) ? (e[r] = u, e[l] = n, r = l) : (e[r] = c, e[s] = n, r = s);
				else if (l < a && 0 > i(u, n)) e[r] = u, e[l] = n, r = l;
				else break a;
			}
		}
		return t;
	}
	function i(e, t) {
		var n = e.sortIndex - t.sortIndex;
		return n === 0 ? e.id - t.id : n;
	}
	if (typeof performance == "object" && typeof performance.now == "function") {
		var a = performance;
		e.unstable_now = function() {
			return a.now();
		};
	} else {
		var o = Date, s = o.now();
		e.unstable_now = function() {
			return o.now() - s;
		};
	}
	var c = [], l = [], u = 1, d = null, f = 3, p = !1, m = !1, h = !1, g = typeof setTimeout == "function" ? setTimeout : null, _ = typeof clearTimeout == "function" ? clearTimeout : null, v = typeof setImmediate < "u" ? setImmediate : null;
	typeof navigator < "u" && navigator.scheduling !== void 0 && navigator.scheduling.isInputPending !== void 0 && navigator.scheduling.isInputPending.bind(navigator.scheduling);
	function y(e) {
		for (var i = n(l); i !== null;) {
			if (i.callback === null) r(l);
			else if (i.startTime <= e) r(l), i.sortIndex = i.expirationTime, t(c, i);
			else break;
			i = n(l);
		}
	}
	function b(e) {
		if (h = !1, y(e), !m) if (n(c) !== null) m = !0, M(x);
		else {
			var t = n(l);
			t !== null && N(b, t.startTime - e);
		}
	}
	function x(t, i) {
		m = !1, h && (h = !1, _(w), w = -1), p = !0;
		var a = f;
		try {
			for (y(i), d = n(c); d !== null && (!(d.expirationTime > i) || t && !D());) {
				var o = d.callback;
				if (typeof o == "function") {
					d.callback = null, f = d.priorityLevel;
					var s = o(d.expirationTime <= i);
					i = e.unstable_now(), typeof s == "function" ? d.callback = s : d === n(c) && r(c), y(i);
				} else r(c);
				d = n(c);
			}
			if (d !== null) var u = !0;
			else {
				var g = n(l);
				g !== null && N(b, g.startTime - i), u = !1;
			}
			return u;
		} finally {
			d = null, f = a, p = !1;
		}
	}
	var S = !1, C = null, w = -1, T = 5, E = -1;
	function D() {
		return !(e.unstable_now() - E < T);
	}
	function O() {
		if (C !== null) {
			var t = e.unstable_now();
			E = t;
			var n = !0;
			try {
				n = C(!0, t);
			} finally {
				n ? k() : (S = !1, C = null);
			}
		} else S = !1;
	}
	var k;
	if (typeof v == "function") k = function() {
		v(O);
	};
	else if (typeof MessageChannel < "u") {
		var A = new MessageChannel(), j = A.port2;
		A.port1.onmessage = O, k = function() {
			j.postMessage(null);
		};
	} else k = function() {
		g(O, 0);
	};
	function M(e) {
		C = e, S || (S = !0, k());
	}
	function N(t, n) {
		w = g(function() {
			t(e.unstable_now());
		}, n);
	}
	e.unstable_IdlePriority = 5, e.unstable_ImmediatePriority = 1, e.unstable_LowPriority = 4, e.unstable_NormalPriority = 3, e.unstable_Profiling = null, e.unstable_UserBlockingPriority = 2, e.unstable_cancelCallback = function(e) {
		e.callback = null;
	}, e.unstable_continueExecution = function() {
		m || p || (m = !0, M(x));
	}, e.unstable_forceFrameRate = function(e) {
		0 > e || 125 < e ? console.error("forceFrameRate takes a positive int between 0 and 125, forcing frame rates higher than 125 fps is not supported") : T = 0 < e ? Math.floor(1e3 / e) : 5;
	}, e.unstable_getCurrentPriorityLevel = function() {
		return f;
	}, e.unstable_getFirstCallbackNode = function() {
		return n(c);
	}, e.unstable_next = function(e) {
		switch (f) {
			case 1:
			case 2:
			case 3:
				var t = 3;
				break;
			default: t = f;
		}
		var n = f;
		f = t;
		try {
			return e();
		} finally {
			f = n;
		}
	}, e.unstable_pauseExecution = function() {}, e.unstable_requestPaint = function() {}, e.unstable_runWithPriority = function(e, t) {
		switch (e) {
			case 1:
			case 2:
			case 3:
			case 4:
			case 5: break;
			default: e = 3;
		}
		var n = f;
		f = e;
		try {
			return t();
		} finally {
			f = n;
		}
	}, e.unstable_scheduleCallback = function(r, i, a) {
		var o = e.unstable_now();
		switch (typeof a == "object" && a ? (a = a.delay, a = typeof a == "number" && 0 < a ? o + a : o) : a = o, r) {
			case 1:
				var s = -1;
				break;
			case 2:
				s = 250;
				break;
			case 5:
				s = 1073741823;
				break;
			case 4:
				s = 1e4;
				break;
			default: s = 5e3;
		}
		return s = a + s, r = {
			id: u++,
			callback: i,
			priorityLevel: r,
			startTime: a,
			expirationTime: s,
			sortIndex: -1
		}, a > o ? (r.sortIndex = a, t(l, r), n(c) === null && r === n(l) && (h ? (_(w), w = -1) : h = !0, N(b, a - o))) : (r.sortIndex = s, t(c, r), m || p || (m = !0, M(x))), r;
	}, e.unstable_shouldYield = D, e.unstable_wrapCallback = function(e) {
		var t = f;
		return function() {
			var n = f;
			f = t;
			try {
				return e.apply(this, arguments);
			} finally {
				f = n;
			}
		};
	};
})), f = /* @__PURE__ */ o(((e, t) => {
	t.exports = d();
})), p = /* @__PURE__ */ o(((e) => {
	var t = u(), n = f();
	function r(e) {
		for (var t = "https://reactjs.org/docs/error-decoder.html?invariant=" + e, n = 1; n < arguments.length; n++) t += "&args[]=" + encodeURIComponent(arguments[n]);
		return "Minified React error #" + e + "; visit " + t + " for the full message or use the non-minified dev environment for full errors and additional helpful warnings.";
	}
	var i = /* @__PURE__ */ new Set(), a = {};
	function o(e, t) {
		s(e, t), s(e + "Capture", t);
	}
	function s(e, t) {
		for (a[e] = t, e = 0; e < t.length; e++) i.add(t[e]);
	}
	var c = !(typeof window > "u" || window.document === void 0 || window.document.createElement === void 0), l = Object.prototype.hasOwnProperty, d = /^[:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD][:A-Z_a-z\u00C0-\u00D6\u00D8-\u00F6\u00F8-\u02FF\u0370-\u037D\u037F-\u1FFF\u200C-\u200D\u2070-\u218F\u2C00-\u2FEF\u3001-\uD7FF\uF900-\uFDCF\uFDF0-\uFFFD\-.0-9\u00B7\u0300-\u036F\u203F-\u2040]*$/, p = {}, m = {};
	function h(e) {
		return l.call(m, e) ? !0 : l.call(p, e) ? !1 : d.test(e) ? m[e] = !0 : (p[e] = !0, !1);
	}
	function g(e, t, n, r) {
		if (n !== null && n.type === 0) return !1;
		switch (typeof t) {
			case "function":
			case "symbol": return !0;
			case "boolean": return r ? !1 : n === null ? (e = e.toLowerCase().slice(0, 5), e !== "data-" && e !== "aria-") : !n.acceptsBooleans;
			default: return !1;
		}
	}
	function _(e, t, n, r) {
		if (t == null || g(e, t, n, r)) return !0;
		if (r) return !1;
		if (n !== null) switch (n.type) {
			case 3: return !t;
			case 4: return !1 === t;
			case 5: return isNaN(t);
			case 6: return isNaN(t) || 1 > t;
		}
		return !1;
	}
	function v(e, t, n, r, i, a, o) {
		this.acceptsBooleans = t === 2 || t === 3 || t === 4, this.attributeName = r, this.attributeNamespace = i, this.mustUseProperty = n, this.propertyName = e, this.type = t, this.sanitizeURL = a, this.removeEmptyString = o;
	}
	var y = {};
	"children dangerouslySetInnerHTML defaultValue defaultChecked innerHTML suppressContentEditableWarning suppressHydrationWarning style".split(" ").forEach(function(e) {
		y[e] = new v(e, 0, !1, e, null, !1, !1);
	}), [
		["acceptCharset", "accept-charset"],
		["className", "class"],
		["htmlFor", "for"],
		["httpEquiv", "http-equiv"]
	].forEach(function(e) {
		var t = e[0];
		y[t] = new v(t, 1, !1, e[1], null, !1, !1);
	}), [
		"contentEditable",
		"draggable",
		"spellCheck",
		"value"
	].forEach(function(e) {
		y[e] = new v(e, 2, !1, e.toLowerCase(), null, !1, !1);
	}), [
		"autoReverse",
		"externalResourcesRequired",
		"focusable",
		"preserveAlpha"
	].forEach(function(e) {
		y[e] = new v(e, 2, !1, e, null, !1, !1);
	}), "allowFullScreen async autoFocus autoPlay controls default defer disabled disablePictureInPicture disableRemotePlayback formNoValidate hidden loop noModule noValidate open playsInline readOnly required reversed scoped seamless itemScope".split(" ").forEach(function(e) {
		y[e] = new v(e, 3, !1, e.toLowerCase(), null, !1, !1);
	}), [
		"checked",
		"multiple",
		"muted",
		"selected"
	].forEach(function(e) {
		y[e] = new v(e, 3, !0, e, null, !1, !1);
	}), ["capture", "download"].forEach(function(e) {
		y[e] = new v(e, 4, !1, e, null, !1, !1);
	}), [
		"cols",
		"rows",
		"size",
		"span"
	].forEach(function(e) {
		y[e] = new v(e, 6, !1, e, null, !1, !1);
	}), ["rowSpan", "start"].forEach(function(e) {
		y[e] = new v(e, 5, !1, e.toLowerCase(), null, !1, !1);
	});
	var b = /[\-:]([a-z])/g;
	function x(e) {
		return e[1].toUpperCase();
	}
	"accent-height alignment-baseline arabic-form baseline-shift cap-height clip-path clip-rule color-interpolation color-interpolation-filters color-profile color-rendering dominant-baseline enable-background fill-opacity fill-rule flood-color flood-opacity font-family font-size font-size-adjust font-stretch font-style font-variant font-weight glyph-name glyph-orientation-horizontal glyph-orientation-vertical horiz-adv-x horiz-origin-x image-rendering letter-spacing lighting-color marker-end marker-mid marker-start overline-position overline-thickness paint-order panose-1 pointer-events rendering-intent shape-rendering stop-color stop-opacity strikethrough-position strikethrough-thickness stroke-dasharray stroke-dashoffset stroke-linecap stroke-linejoin stroke-miterlimit stroke-opacity stroke-width text-anchor text-decoration text-rendering underline-position underline-thickness unicode-bidi unicode-range units-per-em v-alphabetic v-hanging v-ideographic v-mathematical vector-effect vert-adv-y vert-origin-x vert-origin-y word-spacing writing-mode xmlns:xlink x-height".split(" ").forEach(function(e) {
		var t = e.replace(b, x);
		y[t] = new v(t, 1, !1, e, null, !1, !1);
	}), "xlink:actuate xlink:arcrole xlink:role xlink:show xlink:title xlink:type".split(" ").forEach(function(e) {
		var t = e.replace(b, x);
		y[t] = new v(t, 1, !1, e, "http://www.w3.org/1999/xlink", !1, !1);
	}), [
		"xml:base",
		"xml:lang",
		"xml:space"
	].forEach(function(e) {
		var t = e.replace(b, x);
		y[t] = new v(t, 1, !1, e, "http://www.w3.org/XML/1998/namespace", !1, !1);
	}), ["tabIndex", "crossOrigin"].forEach(function(e) {
		y[e] = new v(e, 1, !1, e.toLowerCase(), null, !1, !1);
	}), y.xlinkHref = new v("xlinkHref", 1, !1, "xlink:href", "http://www.w3.org/1999/xlink", !0, !1), [
		"src",
		"href",
		"action",
		"formAction"
	].forEach(function(e) {
		y[e] = new v(e, 1, !1, e.toLowerCase(), null, !0, !0);
	});
	function S(e, t, n, r) {
		var i = y.hasOwnProperty(t) ? y[t] : null;
		(i === null ? r || !(2 < t.length) || t[0] !== "o" && t[0] !== "O" || t[1] !== "n" && t[1] !== "N" : i.type !== 0) && (_(t, n, i, r) && (n = null), r || i === null ? h(t) && (n === null ? e.removeAttribute(t) : e.setAttribute(t, "" + n)) : i.mustUseProperty ? e[i.propertyName] = n === null ? i.type !== 3 && "" : n : (t = i.attributeName, r = i.attributeNamespace, n === null ? e.removeAttribute(t) : (i = i.type, n = i === 3 || i === 4 && !0 === n ? "" : "" + n, r ? e.setAttributeNS(r, t, n) : e.setAttribute(t, n))));
	}
	var C = t.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED, w = Symbol.for("react.element"), T = Symbol.for("react.portal"), E = Symbol.for("react.fragment"), D = Symbol.for("react.strict_mode"), O = Symbol.for("react.profiler"), k = Symbol.for("react.provider"), A = Symbol.for("react.context"), j = Symbol.for("react.forward_ref"), M = Symbol.for("react.suspense"), N = Symbol.for("react.suspense_list"), P = Symbol.for("react.memo"), F = Symbol.for("react.lazy"), I = Symbol.for("react.offscreen"), ee = Symbol.iterator;
	function L(e) {
		return typeof e != "object" || !e ? null : (e = ee && e[ee] || e["@@iterator"], typeof e == "function" ? e : null);
	}
	var R = Object.assign, z;
	function B(e) {
		if (z === void 0) try {
			throw Error();
		} catch (e) {
			var t = e.stack.trim().match(/\n( *(at )?)/);
			z = t && t[1] || "";
		}
		return "\n" + z + e;
	}
	var te = !1;
	function ne(e, t) {
		if (!e || te) return "";
		te = !0;
		var n = Error.prepareStackTrace;
		Error.prepareStackTrace = void 0;
		try {
			if (t) if (t = function() {
				throw Error();
			}, Object.defineProperty(t.prototype, "props", { set: function() {
				throw Error();
			} }), typeof Reflect == "object" && Reflect.construct) {
				try {
					Reflect.construct(t, []);
				} catch (e) {
					var r = e;
				}
				Reflect.construct(e, [], t);
			} else {
				try {
					t.call();
				} catch (e) {
					r = e;
				}
				e.call(t.prototype);
			}
			else {
				try {
					throw Error();
				} catch (e) {
					r = e;
				}
				e();
			}
		} catch (t) {
			if (t && r && typeof t.stack == "string") {
				for (var i = t.stack.split("\n"), a = r.stack.split("\n"), o = i.length - 1, s = a.length - 1; 1 <= o && 0 <= s && i[o] !== a[s];) s--;
				for (; 1 <= o && 0 <= s; o--, s--) if (i[o] !== a[s]) {
					if (o !== 1 || s !== 1) do
						if (o--, s--, 0 > s || i[o] !== a[s]) {
							var c = "\n" + i[o].replace(" at new ", " at ");
							return e.displayName && c.includes("<anonymous>") && (c = c.replace("<anonymous>", e.displayName)), c;
						}
					while (1 <= o && 0 <= s);
					break;
				}
			}
		} finally {
			te = !1, Error.prepareStackTrace = n;
		}
		return (e = e ? e.displayName || e.name : "") ? B(e) : "";
	}
	function re(e) {
		switch (e.tag) {
			case 5: return B(e.type);
			case 16: return B("Lazy");
			case 13: return B("Suspense");
			case 19: return B("SuspenseList");
			case 0:
			case 2:
			case 15: return e = ne(e.type, !1), e;
			case 11: return e = ne(e.type.render, !1), e;
			case 1: return e = ne(e.type, !0), e;
			default: return "";
		}
	}
	function ie(e) {
		if (e == null) return null;
		if (typeof e == "function") return e.displayName || e.name || null;
		if (typeof e == "string") return e;
		switch (e) {
			case E: return "Fragment";
			case T: return "Portal";
			case O: return "Profiler";
			case D: return "StrictMode";
			case M: return "Suspense";
			case N: return "SuspenseList";
		}
		if (typeof e == "object") switch (e.$$typeof) {
			case A: return (e.displayName || "Context") + ".Consumer";
			case k: return (e._context.displayName || "Context") + ".Provider";
			case j:
				var t = e.render;
				return e = e.displayName, e ||= (e = t.displayName || t.name || "", e === "" ? "ForwardRef" : "ForwardRef(" + e + ")"), e;
			case P: return t = e.displayName || null, t === null ? ie(e.type) || "Memo" : t;
			case F:
				t = e._payload, e = e._init;
				try {
					return ie(e(t));
				} catch {}
		}
		return null;
	}
	function ae(e) {
		var t = e.type;
		switch (e.tag) {
			case 24: return "Cache";
			case 9: return (t.displayName || "Context") + ".Consumer";
			case 10: return (t._context.displayName || "Context") + ".Provider";
			case 18: return "DehydratedFragment";
			case 11: return e = t.render, e = e.displayName || e.name || "", t.displayName || (e === "" ? "ForwardRef" : "ForwardRef(" + e + ")");
			case 7: return "Fragment";
			case 5: return t;
			case 4: return "Portal";
			case 3: return "Root";
			case 6: return "Text";
			case 16: return ie(t);
			case 8: return t === D ? "StrictMode" : "Mode";
			case 22: return "Offscreen";
			case 12: return "Profiler";
			case 21: return "Scope";
			case 13: return "Suspense";
			case 19: return "SuspenseList";
			case 25: return "TracingMarker";
			case 1:
			case 0:
			case 17:
			case 2:
			case 14:
			case 15:
				if (typeof t == "function") return t.displayName || t.name || null;
				if (typeof t == "string") return t;
		}
		return null;
	}
	function oe(e) {
		switch (typeof e) {
			case "boolean":
			case "number":
			case "string":
			case "undefined": return e;
			case "object": return e;
			default: return "";
		}
	}
	function se(e) {
		var t = e.type;
		return (e = e.nodeName) && e.toLowerCase() === "input" && (t === "checkbox" || t === "radio");
	}
	function ce(e) {
		var t = se(e) ? "checked" : "value", n = Object.getOwnPropertyDescriptor(e.constructor.prototype, t), r = "" + e[t];
		if (!e.hasOwnProperty(t) && n !== void 0 && typeof n.get == "function" && typeof n.set == "function") {
			var i = n.get, a = n.set;
			return Object.defineProperty(e, t, {
				configurable: !0,
				get: function() {
					return i.call(this);
				},
				set: function(e) {
					r = "" + e, a.call(this, e);
				}
			}), Object.defineProperty(e, t, { enumerable: n.enumerable }), {
				getValue: function() {
					return r;
				},
				setValue: function(e) {
					r = "" + e;
				},
				stopTracking: function() {
					e._valueTracker = null, delete e[t];
				}
			};
		}
	}
	function le(e) {
		e._valueTracker ||= ce(e);
	}
	function ue(e) {
		if (!e) return !1;
		var t = e._valueTracker;
		if (!t) return !0;
		var n = t.getValue(), r = "";
		return e && (r = se(e) ? e.checked ? "true" : "false" : e.value), e = r, e === n ? !1 : (t.setValue(e), !0);
	}
	function de(e) {
		if (e ||= typeof document < "u" ? document : void 0, e === void 0) return null;
		try {
			return e.activeElement || e.body;
		} catch {
			return e.body;
		}
	}
	function fe(e, t) {
		var n = t.checked;
		return R({}, t, {
			defaultChecked: void 0,
			defaultValue: void 0,
			value: void 0,
			checked: n ?? e._wrapperState.initialChecked
		});
	}
	function pe(e, t) {
		var n = t.defaultValue == null ? "" : t.defaultValue, r = t.checked == null ? t.defaultChecked : t.checked;
		n = oe(t.value == null ? n : t.value), e._wrapperState = {
			initialChecked: r,
			initialValue: n,
			controlled: t.type === "checkbox" || t.type === "radio" ? t.checked != null : t.value != null
		};
	}
	function me(e, t) {
		t = t.checked, t != null && S(e, "checked", t, !1);
	}
	function he(e, t) {
		me(e, t);
		var n = oe(t.value), r = t.type;
		if (n != null) r === "number" ? (n === 0 && e.value === "" || e.value != n) && (e.value = "" + n) : e.value !== "" + n && (e.value = "" + n);
		else if (r === "submit" || r === "reset") {
			e.removeAttribute("value");
			return;
		}
		t.hasOwnProperty("value") ? _e(e, t.type, n) : t.hasOwnProperty("defaultValue") && _e(e, t.type, oe(t.defaultValue)), t.checked == null && t.defaultChecked != null && (e.defaultChecked = !!t.defaultChecked);
	}
	function ge(e, t, n) {
		if (t.hasOwnProperty("value") || t.hasOwnProperty("defaultValue")) {
			var r = t.type;
			if (!(r !== "submit" && r !== "reset" || t.value !== void 0 && t.value !== null)) return;
			t = "" + e._wrapperState.initialValue, n || t === e.value || (e.value = t), e.defaultValue = t;
		}
		n = e.name, n !== "" && (e.name = ""), e.defaultChecked = !!e._wrapperState.initialChecked, n !== "" && (e.name = n);
	}
	function _e(e, t, n) {
		(t !== "number" || de(e.ownerDocument) !== e) && (n == null ? e.defaultValue = "" + e._wrapperState.initialValue : e.defaultValue !== "" + n && (e.defaultValue = "" + n));
	}
	var ve = Array.isArray;
	function ye(e, t, n, r) {
		if (e = e.options, t) {
			t = {};
			for (var i = 0; i < n.length; i++) t["$" + n[i]] = !0;
			for (n = 0; n < e.length; n++) i = t.hasOwnProperty("$" + e[n].value), e[n].selected !== i && (e[n].selected = i), i && r && (e[n].defaultSelected = !0);
		} else {
			for (n = "" + oe(n), t = null, i = 0; i < e.length; i++) {
				if (e[i].value === n) {
					e[i].selected = !0, r && (e[i].defaultSelected = !0);
					return;
				}
				t !== null || e[i].disabled || (t = e[i]);
			}
			t !== null && (t.selected = !0);
		}
	}
	function be(e, t) {
		if (t.dangerouslySetInnerHTML != null) throw Error(r(91));
		return R({}, t, {
			value: void 0,
			defaultValue: void 0,
			children: "" + e._wrapperState.initialValue
		});
	}
	function xe(e, t) {
		var n = t.value;
		if (n == null) {
			if (n = t.children, t = t.defaultValue, n != null) {
				if (t != null) throw Error(r(92));
				if (ve(n)) {
					if (1 < n.length) throw Error(r(93));
					n = n[0];
				}
				t = n;
			}
			t ??= "", n = t;
		}
		e._wrapperState = { initialValue: oe(n) };
	}
	function Se(e, t) {
		var n = oe(t.value), r = oe(t.defaultValue);
		n != null && (n = "" + n, n !== e.value && (e.value = n), t.defaultValue == null && e.defaultValue !== n && (e.defaultValue = n)), r != null && (e.defaultValue = "" + r);
	}
	function Ce(e) {
		var t = e.textContent;
		t === e._wrapperState.initialValue && t !== "" && t !== null && (e.value = t);
	}
	function we(e) {
		switch (e) {
			case "svg": return "http://www.w3.org/2000/svg";
			case "math": return "http://www.w3.org/1998/Math/MathML";
			default: return "http://www.w3.org/1999/xhtml";
		}
	}
	function Te(e, t) {
		return e == null || e === "http://www.w3.org/1999/xhtml" ? we(t) : e === "http://www.w3.org/2000/svg" && t === "foreignObject" ? "http://www.w3.org/1999/xhtml" : e;
	}
	var Ee, De = function(e) {
		return typeof MSApp < "u" && MSApp.execUnsafeLocalFunction ? function(t, n, r, i) {
			MSApp.execUnsafeLocalFunction(function() {
				return e(t, n, r, i);
			});
		} : e;
	}(function(e, t) {
		if (e.namespaceURI !== "http://www.w3.org/2000/svg" || "innerHTML" in e) e.innerHTML = t;
		else {
			for (Ee ||= document.createElement("div"), Ee.innerHTML = "<svg>" + t.valueOf().toString() + "</svg>", t = Ee.firstChild; e.firstChild;) e.removeChild(e.firstChild);
			for (; t.firstChild;) e.appendChild(t.firstChild);
		}
	});
	function Oe(e, t) {
		if (t) {
			var n = e.firstChild;
			if (n && n === e.lastChild && n.nodeType === 3) {
				n.nodeValue = t;
				return;
			}
		}
		e.textContent = t;
	}
	var ke = {
		animationIterationCount: !0,
		aspectRatio: !0,
		borderImageOutset: !0,
		borderImageSlice: !0,
		borderImageWidth: !0,
		boxFlex: !0,
		boxFlexGroup: !0,
		boxOrdinalGroup: !0,
		columnCount: !0,
		columns: !0,
		flex: !0,
		flexGrow: !0,
		flexPositive: !0,
		flexShrink: !0,
		flexNegative: !0,
		flexOrder: !0,
		gridArea: !0,
		gridRow: !0,
		gridRowEnd: !0,
		gridRowSpan: !0,
		gridRowStart: !0,
		gridColumn: !0,
		gridColumnEnd: !0,
		gridColumnSpan: !0,
		gridColumnStart: !0,
		fontWeight: !0,
		lineClamp: !0,
		lineHeight: !0,
		opacity: !0,
		order: !0,
		orphans: !0,
		tabSize: !0,
		widows: !0,
		zIndex: !0,
		zoom: !0,
		fillOpacity: !0,
		floodOpacity: !0,
		stopOpacity: !0,
		strokeDasharray: !0,
		strokeDashoffset: !0,
		strokeMiterlimit: !0,
		strokeOpacity: !0,
		strokeWidth: !0
	}, Ae = [
		"Webkit",
		"ms",
		"Moz",
		"O"
	];
	Object.keys(ke).forEach(function(e) {
		Ae.forEach(function(t) {
			t = t + e.charAt(0).toUpperCase() + e.substring(1), ke[t] = ke[e];
		});
	});
	function je(e, t, n) {
		return t == null || typeof t == "boolean" || t === "" ? "" : n || typeof t != "number" || t === 0 || ke.hasOwnProperty(e) && ke[e] ? ("" + t).trim() : t + "px";
	}
	function Me(e, t) {
		for (var n in e = e.style, t) if (t.hasOwnProperty(n)) {
			var r = n.indexOf("--") === 0, i = je(n, t[n], r);
			n === "float" && (n = "cssFloat"), r ? e.setProperty(n, i) : e[n] = i;
		}
	}
	var Ne = R({ menuitem: !0 }, {
		area: !0,
		base: !0,
		br: !0,
		col: !0,
		embed: !0,
		hr: !0,
		img: !0,
		input: !0,
		keygen: !0,
		link: !0,
		meta: !0,
		param: !0,
		source: !0,
		track: !0,
		wbr: !0
	});
	function Pe(e, t) {
		if (t) {
			if (Ne[e] && (t.children != null || t.dangerouslySetInnerHTML != null)) throw Error(r(137, e));
			if (t.dangerouslySetInnerHTML != null) {
				if (t.children != null) throw Error(r(60));
				if (typeof t.dangerouslySetInnerHTML != "object" || !("__html" in t.dangerouslySetInnerHTML)) throw Error(r(61));
			}
			if (t.style != null && typeof t.style != "object") throw Error(r(62));
		}
	}
	function Fe(e, t) {
		if (e.indexOf("-") === -1) return typeof t.is == "string";
		switch (e) {
			case "annotation-xml":
			case "color-profile":
			case "font-face":
			case "font-face-src":
			case "font-face-uri":
			case "font-face-format":
			case "font-face-name":
			case "missing-glyph": return !1;
			default: return !0;
		}
	}
	var Ie = null;
	function Le(e) {
		return e = e.target || e.srcElement || window, e.correspondingUseElement && (e = e.correspondingUseElement), e.nodeType === 3 ? e.parentNode : e;
	}
	var Re = null, ze = null, Be = null;
	function Ve(e) {
		if (e = zi(e)) {
			if (typeof Re != "function") throw Error(r(280));
			var t = e.stateNode;
			t && (t = Vi(t), Re(e.stateNode, e.type, t));
		}
	}
	function He(e) {
		ze ? Be ? Be.push(e) : Be = [e] : ze = e;
	}
	function Ue() {
		if (ze) {
			var e = ze, t = Be;
			if (Be = ze = null, Ve(e), t) for (e = 0; e < t.length; e++) Ve(t[e]);
		}
	}
	function We(e, t) {
		return e(t);
	}
	function Ge() {}
	var Ke = !1;
	function qe(e, t, n) {
		if (Ke) return e(t, n);
		Ke = !0;
		try {
			return We(e, t, n);
		} finally {
			Ke = !1, (ze !== null || Be !== null) && (Ge(), Ue());
		}
	}
	function Je(e, t) {
		var n = e.stateNode;
		if (n === null) return null;
		var i = Vi(n);
		if (i === null) return null;
		n = i[t];
		a: switch (t) {
			case "onClick":
			case "onClickCapture":
			case "onDoubleClick":
			case "onDoubleClickCapture":
			case "onMouseDown":
			case "onMouseDownCapture":
			case "onMouseMove":
			case "onMouseMoveCapture":
			case "onMouseUp":
			case "onMouseUpCapture":
			case "onMouseEnter":
				(i = !i.disabled) || (e = e.type, i = !(e === "button" || e === "input" || e === "select" || e === "textarea")), e = !i;
				break a;
			default: e = !1;
		}
		if (e) return null;
		if (n && typeof n != "function") throw Error(r(231, t, typeof n));
		return n;
	}
	var Ye = !1;
	if (c) try {
		var Xe = {};
		Object.defineProperty(Xe, "passive", { get: function() {
			Ye = !0;
		} }), window.addEventListener("test", Xe, Xe), window.removeEventListener("test", Xe, Xe);
	} catch {
		Ye = !1;
	}
	function Ze(e, t, n, r, i, a, o, s, c) {
		var l = Array.prototype.slice.call(arguments, 3);
		try {
			t.apply(n, l);
		} catch (e) {
			this.onError(e);
		}
	}
	var Qe = !1, $e = null, et = !1, tt = null, nt = { onError: function(e) {
		Qe = !0, $e = e;
	} };
	function rt(e, t, n, r, i, a, o, s, c) {
		Qe = !1, $e = null, Ze.apply(nt, arguments);
	}
	function it(e, t, n, i, a, o, s, c, l) {
		if (rt.apply(this, arguments), Qe) {
			if (Qe) {
				var u = $e;
				Qe = !1, $e = null;
			} else throw Error(r(198));
			et || (et = !0, tt = u);
		}
	}
	function at(e) {
		var t = e, n = e;
		if (e.alternate) for (; t.return;) t = t.return;
		else {
			e = t;
			do
				t = e, t.flags & 4098 && (n = t.return), e = t.return;
			while (e);
		}
		return t.tag === 3 ? n : null;
	}
	function ot(e) {
		if (e.tag === 13) {
			var t = e.memoizedState;
			if (t === null && (e = e.alternate, e !== null && (t = e.memoizedState)), t !== null) return t.dehydrated;
		}
		return null;
	}
	function st(e) {
		if (at(e) !== e) throw Error(r(188));
	}
	function ct(e) {
		var t = e.alternate;
		if (!t) {
			if (t = at(e), t === null) throw Error(r(188));
			return t === e ? e : null;
		}
		for (var n = e, i = t;;) {
			var a = n.return;
			if (a === null) break;
			var o = a.alternate;
			if (o === null) {
				if (i = a.return, i !== null) {
					n = i;
					continue;
				}
				break;
			}
			if (a.child === o.child) {
				for (o = a.child; o;) {
					if (o === n) return st(a), e;
					if (o === i) return st(a), t;
					o = o.sibling;
				}
				throw Error(r(188));
			}
			if (n.return !== i.return) n = a, i = o;
			else {
				for (var s = !1, c = a.child; c;) {
					if (c === n) {
						s = !0, n = a, i = o;
						break;
					}
					if (c === i) {
						s = !0, i = a, n = o;
						break;
					}
					c = c.sibling;
				}
				if (!s) {
					for (c = o.child; c;) {
						if (c === n) {
							s = !0, n = o, i = a;
							break;
						}
						if (c === i) {
							s = !0, i = o, n = a;
							break;
						}
						c = c.sibling;
					}
					if (!s) throw Error(r(189));
				}
			}
			if (n.alternate !== i) throw Error(r(190));
		}
		if (n.tag !== 3) throw Error(r(188));
		return n.stateNode.current === n ? e : t;
	}
	function lt(e) {
		return e = ct(e), e === null ? null : ut(e);
	}
	function ut(e) {
		if (e.tag === 5 || e.tag === 6) return e;
		for (e = e.child; e !== null;) {
			var t = ut(e);
			if (t !== null) return t;
			e = e.sibling;
		}
		return null;
	}
	var dt = n.unstable_scheduleCallback, ft = n.unstable_cancelCallback, pt = n.unstable_shouldYield, mt = n.unstable_requestPaint, ht = n.unstable_now, gt = n.unstable_getCurrentPriorityLevel, _t = n.unstable_ImmediatePriority, vt = n.unstable_UserBlockingPriority, yt = n.unstable_NormalPriority, bt = n.unstable_LowPriority, xt = n.unstable_IdlePriority, St = null, Ct = null;
	function wt(e) {
		if (Ct && typeof Ct.onCommitFiberRoot == "function") try {
			Ct.onCommitFiberRoot(St, e, void 0, (e.current.flags & 128) == 128);
		} catch {}
	}
	var Tt = Math.clz32 ? Math.clz32 : Ot, Et = Math.log, Dt = Math.LN2;
	function Ot(e) {
		return e >>>= 0, e === 0 ? 32 : 31 - (Et(e) / Dt | 0) | 0;
	}
	var kt = 64, At = 4194304;
	function jt(e) {
		switch (e & -e) {
			case 1: return 1;
			case 2: return 2;
			case 4: return 4;
			case 8: return 8;
			case 16: return 16;
			case 32: return 32;
			case 64:
			case 128:
			case 256:
			case 512:
			case 1024:
			case 2048:
			case 4096:
			case 8192:
			case 16384:
			case 32768:
			case 65536:
			case 131072:
			case 262144:
			case 524288:
			case 1048576:
			case 2097152: return e & 4194240;
			case 4194304:
			case 8388608:
			case 16777216:
			case 33554432:
			case 67108864: return e & 130023424;
			case 134217728: return 134217728;
			case 268435456: return 268435456;
			case 536870912: return 536870912;
			case 1073741824: return 1073741824;
			default: return e;
		}
	}
	function Mt(e, t) {
		var n = e.pendingLanes;
		if (n === 0) return 0;
		var r = 0, i = e.suspendedLanes, a = e.pingedLanes, o = n & 268435455;
		if (o !== 0) {
			var s = o & ~i;
			s === 0 ? (a &= o, a !== 0 && (r = jt(a))) : r = jt(s);
		} else o = n & ~i, o === 0 ? a !== 0 && (r = jt(a)) : r = jt(o);
		if (r === 0) return 0;
		if (t !== 0 && t !== r && (t & i) === 0 && (i = r & -r, a = t & -t, i >= a || i === 16 && a & 4194240)) return t;
		if (r & 4 && (r |= n & 16), t = e.entangledLanes, t !== 0) for (e = e.entanglements, t &= r; 0 < t;) n = 31 - Tt(t), i = 1 << n, r |= e[n], t &= ~i;
		return r;
	}
	function Nt(e, t) {
		switch (e) {
			case 1:
			case 2:
			case 4: return t + 250;
			case 8:
			case 16:
			case 32:
			case 64:
			case 128:
			case 256:
			case 512:
			case 1024:
			case 2048:
			case 4096:
			case 8192:
			case 16384:
			case 32768:
			case 65536:
			case 131072:
			case 262144:
			case 524288:
			case 1048576:
			case 2097152: return t + 5e3;
			case 4194304:
			case 8388608:
			case 16777216:
			case 33554432:
			case 67108864: return -1;
			case 134217728:
			case 268435456:
			case 536870912:
			case 1073741824: return -1;
			default: return -1;
		}
	}
	function Pt(e, t) {
		for (var n = e.suspendedLanes, r = e.pingedLanes, i = e.expirationTimes, a = e.pendingLanes; 0 < a;) {
			var o = 31 - Tt(a), s = 1 << o, c = i[o];
			c === -1 ? ((s & n) === 0 || (s & r) !== 0) && (i[o] = Nt(s, t)) : c <= t && (e.expiredLanes |= s), a &= ~s;
		}
	}
	function Ft(e) {
		return e = e.pendingLanes & -1073741825, e === 0 ? e & 1073741824 ? 1073741824 : 0 : e;
	}
	function It() {
		var e = kt;
		return kt <<= 1, !(kt & 4194240) && (kt = 64), e;
	}
	function Lt(e) {
		for (var t = [], n = 0; 31 > n; n++) t.push(e);
		return t;
	}
	function Rt(e, t, n) {
		e.pendingLanes |= t, t !== 536870912 && (e.suspendedLanes = 0, e.pingedLanes = 0), e = e.eventTimes, t = 31 - Tt(t), e[t] = n;
	}
	function zt(e, t) {
		var n = e.pendingLanes & ~t;
		e.pendingLanes = t, e.suspendedLanes = 0, e.pingedLanes = 0, e.expiredLanes &= t, e.mutableReadLanes &= t, e.entangledLanes &= t, t = e.entanglements;
		var r = e.eventTimes;
		for (e = e.expirationTimes; 0 < n;) {
			var i = 31 - Tt(n), a = 1 << i;
			t[i] = 0, r[i] = -1, e[i] = -1, n &= ~a;
		}
	}
	function Bt(e, t) {
		var n = e.entangledLanes |= t;
		for (e = e.entanglements; n;) {
			var r = 31 - Tt(n), i = 1 << r;
			i & t | e[r] & t && (e[r] |= t), n &= ~i;
		}
	}
	var V = 0;
	function Vt(e) {
		return e &= -e, 1 < e ? 4 < e ? e & 268435455 ? 16 : 536870912 : 4 : 1;
	}
	var Ht, Ut, Wt, Gt, Kt, qt = !1, Jt = [], Yt = null, Xt = null, Zt = null, Qt = /* @__PURE__ */ new Map(), $t = /* @__PURE__ */ new Map(), en = [], tn = "mousedown mouseup touchcancel touchend touchstart auxclick dblclick pointercancel pointerdown pointerup dragend dragstart drop compositionend compositionstart keydown keypress keyup input textInput copy cut paste click change contextmenu reset submit".split(" ");
	function nn(e, t) {
		switch (e) {
			case "focusin":
			case "focusout":
				Yt = null;
				break;
			case "dragenter":
			case "dragleave":
				Xt = null;
				break;
			case "mouseover":
			case "mouseout":
				Zt = null;
				break;
			case "pointerover":
			case "pointerout":
				Qt.delete(t.pointerId);
				break;
			case "gotpointercapture":
			case "lostpointercapture": $t.delete(t.pointerId);
		}
	}
	function rn(e, t, n, r, i, a) {
		return e === null || e.nativeEvent !== a ? (e = {
			blockedOn: t,
			domEventName: n,
			eventSystemFlags: r,
			nativeEvent: a,
			targetContainers: [i]
		}, t !== null && (t = zi(t), t !== null && Ut(t)), e) : (e.eventSystemFlags |= r, t = e.targetContainers, i !== null && t.indexOf(i) === -1 && t.push(i), e);
	}
	function an(e, t, n, r, i) {
		switch (t) {
			case "focusin": return Yt = rn(Yt, e, t, n, r, i), !0;
			case "dragenter": return Xt = rn(Xt, e, t, n, r, i), !0;
			case "mouseover": return Zt = rn(Zt, e, t, n, r, i), !0;
			case "pointerover":
				var a = i.pointerId;
				return Qt.set(a, rn(Qt.get(a) || null, e, t, n, r, i)), !0;
			case "gotpointercapture": return a = i.pointerId, $t.set(a, rn($t.get(a) || null, e, t, n, r, i)), !0;
		}
		return !1;
	}
	function on(e) {
		var t = Ri(e.target);
		if (t !== null) {
			var n = at(t);
			if (n !== null) {
				if (t = n.tag, t === 13) {
					if (t = ot(n), t !== null) {
						e.blockedOn = t, Kt(e.priority, function() {
							Wt(n);
						});
						return;
					}
				} else if (t === 3 && n.stateNode.current.memoizedState.isDehydrated) {
					e.blockedOn = n.tag === 3 ? n.stateNode.containerInfo : null;
					return;
				}
			}
		}
		e.blockedOn = null;
	}
	function sn(e) {
		if (e.blockedOn !== null) return !1;
		for (var t = e.targetContainers; 0 < t.length;) {
			var n = vn(e.domEventName, e.eventSystemFlags, t[0], e.nativeEvent);
			if (n === null) {
				n = e.nativeEvent;
				var r = new n.constructor(n.type, n);
				Ie = r, n.target.dispatchEvent(r), Ie = null;
			} else return t = zi(n), t !== null && Ut(t), e.blockedOn = n, !1;
			t.shift();
		}
		return !0;
	}
	function cn(e, t, n) {
		sn(e) && n.delete(t);
	}
	function ln() {
		qt = !1, Yt !== null && sn(Yt) && (Yt = null), Xt !== null && sn(Xt) && (Xt = null), Zt !== null && sn(Zt) && (Zt = null), Qt.forEach(cn), $t.forEach(cn);
	}
	function un(e, t) {
		e.blockedOn === t && (e.blockedOn = null, qt || (qt = !0, n.unstable_scheduleCallback(n.unstable_NormalPriority, ln)));
	}
	function dn(e) {
		function t(t) {
			return un(t, e);
		}
		if (0 < Jt.length) {
			un(Jt[0], e);
			for (var n = 1; n < Jt.length; n++) {
				var r = Jt[n];
				r.blockedOn === e && (r.blockedOn = null);
			}
		}
		for (Yt !== null && un(Yt, e), Xt !== null && un(Xt, e), Zt !== null && un(Zt, e), Qt.forEach(t), $t.forEach(t), n = 0; n < en.length; n++) r = en[n], r.blockedOn === e && (r.blockedOn = null);
		for (; 0 < en.length && (n = en[0], n.blockedOn === null);) on(n), n.blockedOn === null && en.shift();
	}
	var fn = C.ReactCurrentBatchConfig, pn = !0;
	function mn(e, t, n, r) {
		var i = V, a = fn.transition;
		fn.transition = null;
		try {
			V = 1, gn(e, t, n, r);
		} finally {
			V = i, fn.transition = a;
		}
	}
	function hn(e, t, n, r) {
		var i = V, a = fn.transition;
		fn.transition = null;
		try {
			V = 4, gn(e, t, n, r);
		} finally {
			V = i, fn.transition = a;
		}
	}
	function gn(e, t, n, r) {
		if (pn) {
			var i = vn(e, t, n, r);
			if (i === null) ui(e, t, r, _n, n), nn(e, r);
			else if (an(i, e, t, n, r)) r.stopPropagation();
			else if (nn(e, r), t & 4 && -1 < tn.indexOf(e)) {
				for (; i !== null;) {
					var a = zi(i);
					if (a !== null && Ht(a), a = vn(e, t, n, r), a === null && ui(e, t, r, _n, n), a === i) break;
					i = a;
				}
				i !== null && r.stopPropagation();
			} else ui(e, t, r, null, n);
		}
	}
	var _n = null;
	function vn(e, t, n, r) {
		if (_n = null, e = Le(r), e = Ri(e), e !== null) if (t = at(e), t === null) e = null;
		else if (n = t.tag, n === 13) {
			if (e = ot(t), e !== null) return e;
			e = null;
		} else if (n === 3) {
			if (t.stateNode.current.memoizedState.isDehydrated) return t.tag === 3 ? t.stateNode.containerInfo : null;
			e = null;
		} else t !== e && (e = null);
		return _n = e, null;
	}
	function yn(e) {
		switch (e) {
			case "cancel":
			case "click":
			case "close":
			case "contextmenu":
			case "copy":
			case "cut":
			case "auxclick":
			case "dblclick":
			case "dragend":
			case "dragstart":
			case "drop":
			case "focusin":
			case "focusout":
			case "input":
			case "invalid":
			case "keydown":
			case "keypress":
			case "keyup":
			case "mousedown":
			case "mouseup":
			case "paste":
			case "pause":
			case "play":
			case "pointercancel":
			case "pointerdown":
			case "pointerup":
			case "ratechange":
			case "reset":
			case "resize":
			case "seeked":
			case "submit":
			case "touchcancel":
			case "touchend":
			case "touchstart":
			case "volumechange":
			case "change":
			case "selectionchange":
			case "textInput":
			case "compositionstart":
			case "compositionend":
			case "compositionupdate":
			case "beforeblur":
			case "afterblur":
			case "beforeinput":
			case "blur":
			case "fullscreenchange":
			case "focus":
			case "hashchange":
			case "popstate":
			case "select":
			case "selectstart": return 1;
			case "drag":
			case "dragenter":
			case "dragexit":
			case "dragleave":
			case "dragover":
			case "mousemove":
			case "mouseout":
			case "mouseover":
			case "pointermove":
			case "pointerout":
			case "pointerover":
			case "scroll":
			case "toggle":
			case "touchmove":
			case "wheel":
			case "mouseenter":
			case "mouseleave":
			case "pointerenter":
			case "pointerleave": return 4;
			case "message": switch (gt()) {
				case _t: return 1;
				case vt: return 4;
				case yt:
				case bt: return 16;
				case xt: return 536870912;
				default: return 16;
			}
			default: return 16;
		}
	}
	var bn = null, xn = null, Sn = null;
	function Cn() {
		if (Sn) return Sn;
		var e, t = xn, n = t.length, r, i = "value" in bn ? bn.value : bn.textContent, a = i.length;
		for (e = 0; e < n && t[e] === i[e]; e++);
		var o = n - e;
		for (r = 1; r <= o && t[n - r] === i[a - r]; r++);
		return Sn = i.slice(e, 1 < r ? 1 - r : void 0);
	}
	function wn(e) {
		var t = e.keyCode;
		return "charCode" in e ? (e = e.charCode, e === 0 && t === 13 && (e = 13)) : e = t, e === 10 && (e = 13), 32 <= e || e === 13 ? e : 0;
	}
	function Tn() {
		return !0;
	}
	function En() {
		return !1;
	}
	function H(e) {
		function t(t, n, r, i, a) {
			for (var o in this._reactName = t, this._targetInst = r, this.type = n, this.nativeEvent = i, this.target = a, this.currentTarget = null, e) e.hasOwnProperty(o) && (t = e[o], this[o] = t ? t(i) : i[o]);
			return this.isDefaultPrevented = (i.defaultPrevented == null ? !1 === i.returnValue : i.defaultPrevented) ? Tn : En, this.isPropagationStopped = En, this;
		}
		return R(t.prototype, {
			preventDefault: function() {
				this.defaultPrevented = !0;
				var e = this.nativeEvent;
				e && (e.preventDefault ? e.preventDefault() : typeof e.returnValue != "unknown" && (e.returnValue = !1), this.isDefaultPrevented = Tn);
			},
			stopPropagation: function() {
				var e = this.nativeEvent;
				e && (e.stopPropagation ? e.stopPropagation() : typeof e.cancelBubble != "unknown" && (e.cancelBubble = !0), this.isPropagationStopped = Tn);
			},
			persist: function() {},
			isPersistent: Tn
		}), t;
	}
	var Dn = {
		eventPhase: 0,
		bubbles: 0,
		cancelable: 0,
		timeStamp: function(e) {
			return e.timeStamp || Date.now();
		},
		defaultPrevented: 0,
		isTrusted: 0
	}, On = H(Dn), kn = R({}, Dn, {
		view: 0,
		detail: 0
	}), An = H(kn), jn, Mn, Nn, Pn = R({}, kn, {
		screenX: 0,
		screenY: 0,
		clientX: 0,
		clientY: 0,
		pageX: 0,
		pageY: 0,
		ctrlKey: 0,
		shiftKey: 0,
		altKey: 0,
		metaKey: 0,
		getModifierState: Gn,
		button: 0,
		buttons: 0,
		relatedTarget: function(e) {
			return e.relatedTarget === void 0 ? e.fromElement === e.srcElement ? e.toElement : e.fromElement : e.relatedTarget;
		},
		movementX: function(e) {
			return "movementX" in e ? e.movementX : (e !== Nn && (Nn && e.type === "mousemove" ? (jn = e.screenX - Nn.screenX, Mn = e.screenY - Nn.screenY) : Mn = jn = 0, Nn = e), jn);
		},
		movementY: function(e) {
			return "movementY" in e ? e.movementY : Mn;
		}
	}), Fn = H(Pn), In = H(R({}, Pn, { dataTransfer: 0 })), Ln = H(R({}, kn, { relatedTarget: 0 })), Rn = H(R({}, Dn, {
		animationName: 0,
		elapsedTime: 0,
		pseudoElement: 0
	})), zn = H(R({}, Dn, { clipboardData: function(e) {
		return "clipboardData" in e ? e.clipboardData : window.clipboardData;
	} })), Bn = H(R({}, Dn, { data: 0 })), Vn = {
		Esc: "Escape",
		Spacebar: " ",
		Left: "ArrowLeft",
		Up: "ArrowUp",
		Right: "ArrowRight",
		Down: "ArrowDown",
		Del: "Delete",
		Win: "OS",
		Menu: "ContextMenu",
		Apps: "ContextMenu",
		Scroll: "ScrollLock",
		MozPrintableKey: "Unidentified"
	}, Hn = {
		8: "Backspace",
		9: "Tab",
		12: "Clear",
		13: "Enter",
		16: "Shift",
		17: "Control",
		18: "Alt",
		19: "Pause",
		20: "CapsLock",
		27: "Escape",
		32: " ",
		33: "PageUp",
		34: "PageDown",
		35: "End",
		36: "Home",
		37: "ArrowLeft",
		38: "ArrowUp",
		39: "ArrowRight",
		40: "ArrowDown",
		45: "Insert",
		46: "Delete",
		112: "F1",
		113: "F2",
		114: "F3",
		115: "F4",
		116: "F5",
		117: "F6",
		118: "F7",
		119: "F8",
		120: "F9",
		121: "F10",
		122: "F11",
		123: "F12",
		144: "NumLock",
		145: "ScrollLock",
		224: "Meta"
	}, Un = {
		Alt: "altKey",
		Control: "ctrlKey",
		Meta: "metaKey",
		Shift: "shiftKey"
	};
	function Wn(e) {
		var t = this.nativeEvent;
		return t.getModifierState ? t.getModifierState(e) : (e = Un[e]) ? !!t[e] : !1;
	}
	function Gn() {
		return Wn;
	}
	var Kn = H(R({}, kn, {
		key: function(e) {
			if (e.key) {
				var t = Vn[e.key] || e.key;
				if (t !== "Unidentified") return t;
			}
			return e.type === "keypress" ? (e = wn(e), e === 13 ? "Enter" : String.fromCharCode(e)) : e.type === "keydown" || e.type === "keyup" ? Hn[e.keyCode] || "Unidentified" : "";
		},
		code: 0,
		location: 0,
		ctrlKey: 0,
		shiftKey: 0,
		altKey: 0,
		metaKey: 0,
		repeat: 0,
		locale: 0,
		getModifierState: Gn,
		charCode: function(e) {
			return e.type === "keypress" ? wn(e) : 0;
		},
		keyCode: function(e) {
			return e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
		},
		which: function(e) {
			return e.type === "keypress" ? wn(e) : e.type === "keydown" || e.type === "keyup" ? e.keyCode : 0;
		}
	})), qn = H(R({}, Pn, {
		pointerId: 0,
		width: 0,
		height: 0,
		pressure: 0,
		tangentialPressure: 0,
		tiltX: 0,
		tiltY: 0,
		twist: 0,
		pointerType: 0,
		isPrimary: 0
	})), Jn = H(R({}, kn, {
		touches: 0,
		targetTouches: 0,
		changedTouches: 0,
		altKey: 0,
		metaKey: 0,
		ctrlKey: 0,
		shiftKey: 0,
		getModifierState: Gn
	})), Yn = H(R({}, Dn, {
		propertyName: 0,
		elapsedTime: 0,
		pseudoElement: 0
	})), Xn = H(R({}, Pn, {
		deltaX: function(e) {
			return "deltaX" in e ? e.deltaX : "wheelDeltaX" in e ? -e.wheelDeltaX : 0;
		},
		deltaY: function(e) {
			return "deltaY" in e ? e.deltaY : "wheelDeltaY" in e ? -e.wheelDeltaY : "wheelDelta" in e ? -e.wheelDelta : 0;
		},
		deltaZ: 0,
		deltaMode: 0
	})), Zn = [
		9,
		13,
		27,
		32
	], Qn = c && "CompositionEvent" in window, $n = null;
	c && "documentMode" in document && ($n = document.documentMode);
	var er = c && "TextEvent" in window && !$n, tr = c && (!Qn || $n && 8 < $n && 11 >= $n), nr = " ", rr = !1;
	function ir(e, t) {
		switch (e) {
			case "keyup": return Zn.indexOf(t.keyCode) !== -1;
			case "keydown": return t.keyCode !== 229;
			case "keypress":
			case "mousedown":
			case "focusout": return !0;
			default: return !1;
		}
	}
	function ar(e) {
		return e = e.detail, typeof e == "object" && "data" in e ? e.data : null;
	}
	var or = !1;
	function sr(e, t) {
		switch (e) {
			case "compositionend": return ar(t);
			case "keypress": return t.which === 32 ? (rr = !0, nr) : null;
			case "textInput": return e = t.data, e === nr && rr ? null : e;
			default: return null;
		}
	}
	function cr(e, t) {
		if (or) return e === "compositionend" || !Qn && ir(e, t) ? (e = Cn(), Sn = xn = bn = null, or = !1, e) : null;
		switch (e) {
			case "paste": return null;
			case "keypress":
				if (!(t.ctrlKey || t.altKey || t.metaKey) || t.ctrlKey && t.altKey) {
					if (t.char && 1 < t.char.length) return t.char;
					if (t.which) return String.fromCharCode(t.which);
				}
				return null;
			case "compositionend": return tr && t.locale !== "ko" ? null : t.data;
			default: return null;
		}
	}
	var lr = {
		color: !0,
		date: !0,
		datetime: !0,
		"datetime-local": !0,
		email: !0,
		month: !0,
		number: !0,
		password: !0,
		range: !0,
		search: !0,
		tel: !0,
		text: !0,
		time: !0,
		url: !0,
		week: !0
	};
	function ur(e) {
		var t = e && e.nodeName && e.nodeName.toLowerCase();
		return t === "input" ? !!lr[e.type] : t === "textarea";
	}
	function dr(e, t, n, r) {
		He(r), t = fi(t, "onChange"), 0 < t.length && (n = new On("onChange", "change", null, n, r), e.push({
			event: n,
			listeners: t
		}));
	}
	var fr = null, pr = null;
	function mr(e) {
		ai(e, 0);
	}
	function hr(e) {
		if (ue(Bi(e))) return e;
	}
	function gr(e, t) {
		if (e === "change") return t;
	}
	var _r = !1;
	if (c) {
		var vr;
		if (c) {
			var yr = "oninput" in document;
			if (!yr) {
				var br = document.createElement("div");
				br.setAttribute("oninput", "return;"), yr = typeof br.oninput == "function";
			}
			vr = yr;
		} else vr = !1;
		_r = vr && (!document.documentMode || 9 < document.documentMode);
	}
	function xr() {
		fr && (fr.detachEvent("onpropertychange", Sr), pr = fr = null);
	}
	function Sr(e) {
		if (e.propertyName === "value" && hr(pr)) {
			var t = [];
			dr(t, pr, e, Le(e)), qe(mr, t);
		}
	}
	function Cr(e, t, n) {
		e === "focusin" ? (xr(), fr = t, pr = n, fr.attachEvent("onpropertychange", Sr)) : e === "focusout" && xr();
	}
	function wr(e) {
		if (e === "selectionchange" || e === "keyup" || e === "keydown") return hr(pr);
	}
	function Tr(e, t) {
		if (e === "click") return hr(t);
	}
	function Er(e, t) {
		if (e === "input" || e === "change") return hr(t);
	}
	function Dr(e, t) {
		return e === t && (e !== 0 || 1 / e == 1 / t) || e !== e && t !== t;
	}
	var Or = typeof Object.is == "function" ? Object.is : Dr;
	function kr(e, t) {
		if (Or(e, t)) return !0;
		if (typeof e != "object" || !e || typeof t != "object" || !t) return !1;
		var n = Object.keys(e), r = Object.keys(t);
		if (n.length !== r.length) return !1;
		for (r = 0; r < n.length; r++) {
			var i = n[r];
			if (!l.call(t, i) || !Or(e[i], t[i])) return !1;
		}
		return !0;
	}
	function Ar(e) {
		for (; e && e.firstChild;) e = e.firstChild;
		return e;
	}
	function jr(e, t) {
		var n = Ar(e);
		e = 0;
		for (var r; n;) {
			if (n.nodeType === 3) {
				if (r = e + n.textContent.length, e <= t && r >= t) return {
					node: n,
					offset: t - e
				};
				e = r;
			}
			a: {
				for (; n;) {
					if (n.nextSibling) {
						n = n.nextSibling;
						break a;
					}
					n = n.parentNode;
				}
				n = void 0;
			}
			n = Ar(n);
		}
	}
	function Mr(e, t) {
		return e && t ? e === t ? !0 : e && e.nodeType === 3 ? !1 : t && t.nodeType === 3 ? Mr(e, t.parentNode) : "contains" in e ? e.contains(t) : e.compareDocumentPosition ? !!(e.compareDocumentPosition(t) & 16) : !1 : !1;
	}
	function Nr() {
		for (var e = window, t = de(); t instanceof e.HTMLIFrameElement;) {
			try {
				var n = typeof t.contentWindow.location.href == "string";
			} catch {
				n = !1;
			}
			if (n) e = t.contentWindow;
			else break;
			t = de(e.document);
		}
		return t;
	}
	function Pr(e) {
		var t = e && e.nodeName && e.nodeName.toLowerCase();
		return t && (t === "input" && (e.type === "text" || e.type === "search" || e.type === "tel" || e.type === "url" || e.type === "password") || t === "textarea" || e.contentEditable === "true");
	}
	function Fr(e) {
		var t = Nr(), n = e.focusedElem, r = e.selectionRange;
		if (t !== n && n && n.ownerDocument && Mr(n.ownerDocument.documentElement, n)) {
			if (r !== null && Pr(n)) {
				if (t = r.start, e = r.end, e === void 0 && (e = t), "selectionStart" in n) n.selectionStart = t, n.selectionEnd = Math.min(e, n.value.length);
				else if (e = (t = n.ownerDocument || document) && t.defaultView || window, e.getSelection) {
					e = e.getSelection();
					var i = n.textContent.length, a = Math.min(r.start, i);
					r = r.end === void 0 ? a : Math.min(r.end, i), !e.extend && a > r && (i = r, r = a, a = i), i = jr(n, a);
					var o = jr(n, r);
					i && o && (e.rangeCount !== 1 || e.anchorNode !== i.node || e.anchorOffset !== i.offset || e.focusNode !== o.node || e.focusOffset !== o.offset) && (t = t.createRange(), t.setStart(i.node, i.offset), e.removeAllRanges(), a > r ? (e.addRange(t), e.extend(o.node, o.offset)) : (t.setEnd(o.node, o.offset), e.addRange(t)));
				}
			}
			for (t = [], e = n; e = e.parentNode;) e.nodeType === 1 && t.push({
				element: e,
				left: e.scrollLeft,
				top: e.scrollTop
			});
			for (typeof n.focus == "function" && n.focus(), n = 0; n < t.length; n++) e = t[n], e.element.scrollLeft = e.left, e.element.scrollTop = e.top;
		}
	}
	var Ir = c && "documentMode" in document && 11 >= document.documentMode, Lr = null, Rr = null, zr = null, Br = !1;
	function Vr(e, t, n) {
		var r = n.window === n ? n.document : n.nodeType === 9 ? n : n.ownerDocument;
		Br || Lr == null || Lr !== de(r) || (r = Lr, "selectionStart" in r && Pr(r) ? r = {
			start: r.selectionStart,
			end: r.selectionEnd
		} : (r = (r.ownerDocument && r.ownerDocument.defaultView || window).getSelection(), r = {
			anchorNode: r.anchorNode,
			anchorOffset: r.anchorOffset,
			focusNode: r.focusNode,
			focusOffset: r.focusOffset
		}), zr && kr(zr, r) || (zr = r, r = fi(Rr, "onSelect"), 0 < r.length && (t = new On("onSelect", "select", null, t, n), e.push({
			event: t,
			listeners: r
		}), t.target = Lr)));
	}
	function Hr(e, t) {
		var n = {};
		return n[e.toLowerCase()] = t.toLowerCase(), n["Webkit" + e] = "webkit" + t, n["Moz" + e] = "moz" + t, n;
	}
	var Ur = {
		animationend: Hr("Animation", "AnimationEnd"),
		animationiteration: Hr("Animation", "AnimationIteration"),
		animationstart: Hr("Animation", "AnimationStart"),
		transitionend: Hr("Transition", "TransitionEnd")
	}, Wr = {}, Gr = {};
	c && (Gr = document.createElement("div").style, "AnimationEvent" in window || (delete Ur.animationend.animation, delete Ur.animationiteration.animation, delete Ur.animationstart.animation), "TransitionEvent" in window || delete Ur.transitionend.transition);
	function Kr(e) {
		if (Wr[e]) return Wr[e];
		if (!Ur[e]) return e;
		var t = Ur[e], n;
		for (n in t) if (t.hasOwnProperty(n) && n in Gr) return Wr[e] = t[n];
		return e;
	}
	var qr = Kr("animationend"), Jr = Kr("animationiteration"), Yr = Kr("animationstart"), Xr = Kr("transitionend"), Zr = /* @__PURE__ */ new Map(), Qr = "abort auxClick cancel canPlay canPlayThrough click close contextMenu copy cut drag dragEnd dragEnter dragExit dragLeave dragOver dragStart drop durationChange emptied encrypted ended error gotPointerCapture input invalid keyDown keyPress keyUp load loadedData loadedMetadata loadStart lostPointerCapture mouseDown mouseMove mouseOut mouseOver mouseUp paste pause play playing pointerCancel pointerDown pointerMove pointerOut pointerOver pointerUp progress rateChange reset resize seeked seeking stalled submit suspend timeUpdate touchCancel touchEnd touchStart volumeChange scroll toggle touchMove waiting wheel".split(" ");
	function $r(e, t) {
		Zr.set(e, t), o(t, [e]);
	}
	for (var ei = 0; ei < Qr.length; ei++) {
		var ti = Qr[ei];
		$r(ti.toLowerCase(), "on" + (ti[0].toUpperCase() + ti.slice(1)));
	}
	$r(qr, "onAnimationEnd"), $r(Jr, "onAnimationIteration"), $r(Yr, "onAnimationStart"), $r("dblclick", "onDoubleClick"), $r("focusin", "onFocus"), $r("focusout", "onBlur"), $r(Xr, "onTransitionEnd"), s("onMouseEnter", ["mouseout", "mouseover"]), s("onMouseLeave", ["mouseout", "mouseover"]), s("onPointerEnter", ["pointerout", "pointerover"]), s("onPointerLeave", ["pointerout", "pointerover"]), o("onChange", "change click focusin focusout input keydown keyup selectionchange".split(" ")), o("onSelect", "focusout contextmenu dragend focusin keydown keyup mousedown mouseup selectionchange".split(" ")), o("onBeforeInput", [
		"compositionend",
		"keypress",
		"textInput",
		"paste"
	]), o("onCompositionEnd", "compositionend focusout keydown keypress keyup mousedown".split(" ")), o("onCompositionStart", "compositionstart focusout keydown keypress keyup mousedown".split(" ")), o("onCompositionUpdate", "compositionupdate focusout keydown keypress keyup mousedown".split(" "));
	var ni = "abort canplay canplaythrough durationchange emptied encrypted ended error loadeddata loadedmetadata loadstart pause play playing progress ratechange resize seeked seeking stalled suspend timeupdate volumechange waiting".split(" "), ri = new Set("cancel close invalid load scroll toggle".split(" ").concat(ni));
	function ii(e, t, n) {
		var r = e.type || "unknown-event";
		e.currentTarget = n, it(r, t, void 0, e), e.currentTarget = null;
	}
	function ai(e, t) {
		t = (t & 4) != 0;
		for (var n = 0; n < e.length; n++) {
			var r = e[n], i = r.event;
			r = r.listeners;
			a: {
				var a = void 0;
				if (t) for (var o = r.length - 1; 0 <= o; o--) {
					var s = r[o], c = s.instance, l = s.currentTarget;
					if (s = s.listener, c !== a && i.isPropagationStopped()) break a;
					ii(i, s, l), a = c;
				}
				else for (o = 0; o < r.length; o++) {
					if (s = r[o], c = s.instance, l = s.currentTarget, s = s.listener, c !== a && i.isPropagationStopped()) break a;
					ii(i, s, l), a = c;
				}
			}
		}
		if (et) throw e = tt, et = !1, tt = null, e;
	}
	function U(e, t) {
		var n = t[Fi];
		n === void 0 && (n = t[Fi] = /* @__PURE__ */ new Set());
		var r = e + "__bubble";
		n.has(r) || (li(t, e, 2, !1), n.add(r));
	}
	function oi(e, t, n) {
		var r = 0;
		t && (r |= 4), li(n, e, r, t);
	}
	var si = "_reactListening" + Math.random().toString(36).slice(2);
	function ci(e) {
		if (!e[si]) {
			e[si] = !0, i.forEach(function(t) {
				t !== "selectionchange" && (ri.has(t) || oi(t, !1, e), oi(t, !0, e));
			});
			var t = e.nodeType === 9 ? e : e.ownerDocument;
			t === null || t[si] || (t[si] = !0, oi("selectionchange", !1, t));
		}
	}
	function li(e, t, n, r) {
		switch (yn(t)) {
			case 1:
				var i = mn;
				break;
			case 4:
				i = hn;
				break;
			default: i = gn;
		}
		n = i.bind(null, t, n, e), i = void 0, !Ye || t !== "touchstart" && t !== "touchmove" && t !== "wheel" || (i = !0), r ? i === void 0 ? e.addEventListener(t, n, !0) : e.addEventListener(t, n, {
			capture: !0,
			passive: i
		}) : i === void 0 ? e.addEventListener(t, n, !1) : e.addEventListener(t, n, { passive: i });
	}
	function ui(e, t, n, r, i) {
		var a = r;
		if (!(t & 1) && !(t & 2) && r !== null) a: for (;;) {
			if (r === null) return;
			var o = r.tag;
			if (o === 3 || o === 4) {
				var s = r.stateNode.containerInfo;
				if (s === i || s.nodeType === 8 && s.parentNode === i) break;
				if (o === 4) for (o = r.return; o !== null;) {
					var c = o.tag;
					if ((c === 3 || c === 4) && (c = o.stateNode.containerInfo, c === i || c.nodeType === 8 && c.parentNode === i)) return;
					o = o.return;
				}
				for (; s !== null;) {
					if (o = Ri(s), o === null) return;
					if (c = o.tag, c === 5 || c === 6) {
						r = a = o;
						continue a;
					}
					s = s.parentNode;
				}
			}
			r = r.return;
		}
		qe(function() {
			var r = a, i = Le(n), o = [];
			a: {
				var s = Zr.get(e);
				if (s !== void 0) {
					var c = On, l = e;
					switch (e) {
						case "keypress": if (wn(n) === 0) break a;
						case "keydown":
						case "keyup":
							c = Kn;
							break;
						case "focusin":
							l = "focus", c = Ln;
							break;
						case "focusout":
							l = "blur", c = Ln;
							break;
						case "beforeblur":
						case "afterblur":
							c = Ln;
							break;
						case "click": if (n.button === 2) break a;
						case "auxclick":
						case "dblclick":
						case "mousedown":
						case "mousemove":
						case "mouseup":
						case "mouseout":
						case "mouseover":
						case "contextmenu":
							c = Fn;
							break;
						case "drag":
						case "dragend":
						case "dragenter":
						case "dragexit":
						case "dragleave":
						case "dragover":
						case "dragstart":
						case "drop":
							c = In;
							break;
						case "touchcancel":
						case "touchend":
						case "touchmove":
						case "touchstart":
							c = Jn;
							break;
						case qr:
						case Jr:
						case Yr:
							c = Rn;
							break;
						case Xr:
							c = Yn;
							break;
						case "scroll":
							c = An;
							break;
						case "wheel":
							c = Xn;
							break;
						case "copy":
						case "cut":
						case "paste":
							c = zn;
							break;
						case "gotpointercapture":
						case "lostpointercapture":
						case "pointercancel":
						case "pointerdown":
						case "pointermove":
						case "pointerout":
						case "pointerover":
						case "pointerup": c = qn;
					}
					var u = (t & 4) != 0, d = !u && e === "scroll", f = u ? s === null ? null : s + "Capture" : s;
					u = [];
					for (var p = r, m; p !== null;) {
						m = p;
						var h = m.stateNode;
						if (m.tag === 5 && h !== null && (m = h, f !== null && (h = Je(p, f), h != null && u.push(di(p, h, m)))), d) break;
						p = p.return;
					}
					0 < u.length && (s = new c(s, l, null, n, i), o.push({
						event: s,
						listeners: u
					}));
				}
			}
			if (!(t & 7)) {
				a: {
					if (s = e === "mouseover" || e === "pointerover", c = e === "mouseout" || e === "pointerout", s && n !== Ie && (l = n.relatedTarget || n.fromElement) && (Ri(l) || l[Pi])) break a;
					if ((c || s) && (s = i.window === i ? i : (s = i.ownerDocument) ? s.defaultView || s.parentWindow : window, c ? (l = n.relatedTarget || n.toElement, c = r, l = l ? Ri(l) : null, l !== null && (d = at(l), l !== d || l.tag !== 5 && l.tag !== 6) && (l = null)) : (c = null, l = r), c !== l)) {
						if (u = Fn, h = "onMouseLeave", f = "onMouseEnter", p = "mouse", (e === "pointerout" || e === "pointerover") && (u = qn, h = "onPointerLeave", f = "onPointerEnter", p = "pointer"), d = c == null ? s : Bi(c), m = l == null ? s : Bi(l), s = new u(h, p + "leave", c, n, i), s.target = d, s.relatedTarget = m, h = null, Ri(i) === r && (u = new u(f, p + "enter", l, n, i), u.target = m, u.relatedTarget = d, h = u), d = h, c && l) b: {
							for (u = c, f = l, p = 0, m = u; m; m = pi(m)) p++;
							for (m = 0, h = f; h; h = pi(h)) m++;
							for (; 0 < p - m;) u = pi(u), p--;
							for (; 0 < m - p;) f = pi(f), m--;
							for (; p--;) {
								if (u === f || f !== null && u === f.alternate) break b;
								u = pi(u), f = pi(f);
							}
							u = null;
						}
						else u = null;
						c !== null && mi(o, s, c, u, !1), l !== null && d !== null && mi(o, d, l, u, !0);
					}
				}
				a: {
					if (s = r ? Bi(r) : window, c = s.nodeName && s.nodeName.toLowerCase(), c === "select" || c === "input" && s.type === "file") var g = gr;
					else if (ur(s)) if (_r) g = Er;
					else {
						g = wr;
						var _ = Cr;
					}
					else (c = s.nodeName) && c.toLowerCase() === "input" && (s.type === "checkbox" || s.type === "radio") && (g = Tr);
					if (g &&= g(e, r)) {
						dr(o, g, n, i);
						break a;
					}
					_ && _(e, s, r), e === "focusout" && (_ = s._wrapperState) && _.controlled && s.type === "number" && _e(s, "number", s.value);
				}
				switch (_ = r ? Bi(r) : window, e) {
					case "focusin":
						(ur(_) || _.contentEditable === "true") && (Lr = _, Rr = r, zr = null);
						break;
					case "focusout":
						zr = Rr = Lr = null;
						break;
					case "mousedown":
						Br = !0;
						break;
					case "contextmenu":
					case "mouseup":
					case "dragend":
						Br = !1, Vr(o, n, i);
						break;
					case "selectionchange": if (Ir) break;
					case "keydown":
					case "keyup": Vr(o, n, i);
				}
				var v;
				if (Qn) b: {
					switch (e) {
						case "compositionstart":
							var y = "onCompositionStart";
							break b;
						case "compositionend":
							y = "onCompositionEnd";
							break b;
						case "compositionupdate":
							y = "onCompositionUpdate";
							break b;
					}
					y = void 0;
				}
				else or ? ir(e, n) && (y = "onCompositionEnd") : e === "keydown" && n.keyCode === 229 && (y = "onCompositionStart");
				y && (tr && n.locale !== "ko" && (or || y !== "onCompositionStart" ? y === "onCompositionEnd" && or && (v = Cn()) : (bn = i, xn = "value" in bn ? bn.value : bn.textContent, or = !0)), _ = fi(r, y), 0 < _.length && (y = new Bn(y, e, null, n, i), o.push({
					event: y,
					listeners: _
				}), v ? y.data = v : (v = ar(n), v !== null && (y.data = v)))), (v = er ? sr(e, n) : cr(e, n)) && (r = fi(r, "onBeforeInput"), 0 < r.length && (i = new Bn("onBeforeInput", "beforeinput", null, n, i), o.push({
					event: i,
					listeners: r
				}), i.data = v));
			}
			ai(o, t);
		});
	}
	function di(e, t, n) {
		return {
			instance: e,
			listener: t,
			currentTarget: n
		};
	}
	function fi(e, t) {
		for (var n = t + "Capture", r = []; e !== null;) {
			var i = e, a = i.stateNode;
			i.tag === 5 && a !== null && (i = a, a = Je(e, n), a != null && r.unshift(di(e, a, i)), a = Je(e, t), a != null && r.push(di(e, a, i))), e = e.return;
		}
		return r;
	}
	function pi(e) {
		if (e === null) return null;
		do
			e = e.return;
		while (e && e.tag !== 5);
		return e || null;
	}
	function mi(e, t, n, r, i) {
		for (var a = t._reactName, o = []; n !== null && n !== r;) {
			var s = n, c = s.alternate, l = s.stateNode;
			if (c !== null && c === r) break;
			s.tag === 5 && l !== null && (s = l, i ? (c = Je(n, a), c != null && o.unshift(di(n, c, s))) : i || (c = Je(n, a), c != null && o.push(di(n, c, s)))), n = n.return;
		}
		o.length !== 0 && e.push({
			event: t,
			listeners: o
		});
	}
	var hi = /\r\n?/g, gi = /\u0000|\uFFFD/g;
	function _i(e) {
		return (typeof e == "string" ? e : "" + e).replace(hi, "\n").replace(gi, "");
	}
	function vi(e, t, n) {
		if (t = _i(t), _i(e) !== t && n) throw Error(r(425));
	}
	function yi() {}
	var bi = null, xi = null;
	function Si(e, t) {
		return e === "textarea" || e === "noscript" || typeof t.children == "string" || typeof t.children == "number" || typeof t.dangerouslySetInnerHTML == "object" && t.dangerouslySetInnerHTML !== null && t.dangerouslySetInnerHTML.__html != null;
	}
	var Ci = typeof setTimeout == "function" ? setTimeout : void 0, wi = typeof clearTimeout == "function" ? clearTimeout : void 0, Ti = typeof Promise == "function" ? Promise : void 0, Ei = typeof queueMicrotask == "function" ? queueMicrotask : Ti === void 0 ? Ci : function(e) {
		return Ti.resolve(null).then(e).catch(Di);
	};
	function Di(e) {
		setTimeout(function() {
			throw e;
		});
	}
	function Oi(e, t) {
		var n = t, r = 0;
		do {
			var i = n.nextSibling;
			if (e.removeChild(n), i && i.nodeType === 8) if (n = i.data, n === "/$") {
				if (r === 0) {
					e.removeChild(i), dn(t);
					return;
				}
				r--;
			} else n !== "$" && n !== "$?" && n !== "$!" || r++;
			n = i;
		} while (n);
		dn(t);
	}
	function ki(e) {
		for (; e != null; e = e.nextSibling) {
			var t = e.nodeType;
			if (t === 1 || t === 3) break;
			if (t === 8) {
				if (t = e.data, t === "$" || t === "$!" || t === "$?") break;
				if (t === "/$") return null;
			}
		}
		return e;
	}
	function Ai(e) {
		e = e.previousSibling;
		for (var t = 0; e;) {
			if (e.nodeType === 8) {
				var n = e.data;
				if (n === "$" || n === "$!" || n === "$?") {
					if (t === 0) return e;
					t--;
				} else n === "/$" && t++;
			}
			e = e.previousSibling;
		}
		return null;
	}
	var ji = Math.random().toString(36).slice(2), Mi = "__reactFiber$" + ji, Ni = "__reactProps$" + ji, Pi = "__reactContainer$" + ji, Fi = "__reactEvents$" + ji, Ii = "__reactListeners$" + ji, Li = "__reactHandles$" + ji;
	function Ri(e) {
		var t = e[Mi];
		if (t) return t;
		for (var n = e.parentNode; n;) {
			if (t = n[Pi] || n[Mi]) {
				if (n = t.alternate, t.child !== null || n !== null && n.child !== null) for (e = Ai(e); e !== null;) {
					if (n = e[Mi]) return n;
					e = Ai(e);
				}
				return t;
			}
			e = n, n = e.parentNode;
		}
		return null;
	}
	function zi(e) {
		return e = e[Mi] || e[Pi], !e || e.tag !== 5 && e.tag !== 6 && e.tag !== 13 && e.tag !== 3 ? null : e;
	}
	function Bi(e) {
		if (e.tag === 5 || e.tag === 6) return e.stateNode;
		throw Error(r(33));
	}
	function Vi(e) {
		return e[Ni] || null;
	}
	var Hi = [], Ui = -1;
	function Wi(e) {
		return { current: e };
	}
	function W(e) {
		0 > Ui || (e.current = Hi[Ui], Hi[Ui] = null, Ui--);
	}
	function G(e, t) {
		Ui++, Hi[Ui] = e.current, e.current = t;
	}
	var Gi = {}, Ki = Wi(Gi), qi = Wi(!1), Ji = Gi;
	function Yi(e, t) {
		var n = e.type.contextTypes;
		if (!n) return Gi;
		var r = e.stateNode;
		if (r && r.__reactInternalMemoizedUnmaskedChildContext === t) return r.__reactInternalMemoizedMaskedChildContext;
		var i = {}, a;
		for (a in n) i[a] = t[a];
		return r && (e = e.stateNode, e.__reactInternalMemoizedUnmaskedChildContext = t, e.__reactInternalMemoizedMaskedChildContext = i), i;
	}
	function Xi(e) {
		return e = e.childContextTypes, e != null;
	}
	function Zi() {
		W(qi), W(Ki);
	}
	function Qi(e, t, n) {
		if (Ki.current !== Gi) throw Error(r(168));
		G(Ki, t), G(qi, n);
	}
	function $i(e, t, n) {
		var i = e.stateNode;
		if (t = t.childContextTypes, typeof i.getChildContext != "function") return n;
		for (var a in i = i.getChildContext(), i) if (!(a in t)) throw Error(r(108, ae(e) || "Unknown", a));
		return R({}, n, i);
	}
	function ea(e) {
		return e = (e = e.stateNode) && e.__reactInternalMemoizedMergedChildContext || Gi, Ji = Ki.current, G(Ki, e), G(qi, qi.current), !0;
	}
	function ta(e, t, n) {
		var i = e.stateNode;
		if (!i) throw Error(r(169));
		n ? (e = $i(e, t, Ji), i.__reactInternalMemoizedMergedChildContext = e, W(qi), W(Ki), G(Ki, e)) : W(qi), G(qi, n);
	}
	var na = null, ra = !1, ia = !1;
	function aa(e) {
		na === null ? na = [e] : na.push(e);
	}
	function oa(e) {
		ra = !0, aa(e);
	}
	function sa() {
		if (!ia && na !== null) {
			ia = !0;
			var e = 0, t = V;
			try {
				var n = na;
				for (V = 1; e < n.length; e++) {
					var r = n[e];
					do
						r = r(!0);
					while (r !== null);
				}
				na = null, ra = !1;
			} catch (t) {
				throw na !== null && (na = na.slice(e + 1)), dt(_t, sa), t;
			} finally {
				V = t, ia = !1;
			}
		}
		return null;
	}
	var ca = [], la = 0, ua = null, da = 0, fa = [], pa = 0, ma = null, ha = 1, ga = "";
	function _a(e, t) {
		ca[la++] = da, ca[la++] = ua, ua = e, da = t;
	}
	function va(e, t, n) {
		fa[pa++] = ha, fa[pa++] = ga, fa[pa++] = ma, ma = e;
		var r = ha;
		e = ga;
		var i = 32 - Tt(r) - 1;
		r &= ~(1 << i), n += 1;
		var a = 32 - Tt(t) + i;
		if (30 < a) {
			var o = i - i % 5;
			a = (r & (1 << o) - 1).toString(32), r >>= o, i -= o, ha = 1 << 32 - Tt(t) + i | n << i | r, ga = a + e;
		} else ha = 1 << a | n << i | r, ga = e;
	}
	function ya(e) {
		e.return !== null && (_a(e, 1), va(e, 1, 0));
	}
	function ba(e) {
		for (; e === ua;) ua = ca[--la], ca[la] = null, da = ca[--la], ca[la] = null;
		for (; e === ma;) ma = fa[--pa], fa[pa] = null, ga = fa[--pa], fa[pa] = null, ha = fa[--pa], fa[pa] = null;
	}
	var xa = null, Sa = null, K = !1, Ca = null;
	function q(e, t) {
		var n = Kl(5, null, null, 0);
		n.elementType = "DELETED", n.stateNode = t, n.return = e, t = e.deletions, t === null ? (e.deletions = [n], e.flags |= 16) : t.push(n);
	}
	function wa(e, t) {
		switch (e.tag) {
			case 5:
				var n = e.type;
				return t = t.nodeType !== 1 || n.toLowerCase() !== t.nodeName.toLowerCase() ? null : t, t === null ? !1 : (e.stateNode = t, xa = e, Sa = ki(t.firstChild), !0);
			case 6: return t = e.pendingProps === "" || t.nodeType !== 3 ? null : t, t === null ? !1 : (e.stateNode = t, xa = e, Sa = null, !0);
			case 13: return t = t.nodeType === 8 ? t : null, t === null ? !1 : (n = ma === null ? null : {
				id: ha,
				overflow: ga
			}, e.memoizedState = {
				dehydrated: t,
				treeContext: n,
				retryLane: 1073741824
			}, n = Kl(18, null, null, 0), n.stateNode = t, n.return = e, e.child = n, xa = e, Sa = null, !0);
			default: return !1;
		}
	}
	function Ta(e) {
		return (e.mode & 1) != 0 && (e.flags & 128) == 0;
	}
	function Ea(e) {
		if (K) {
			var t = Sa;
			if (t) {
				var n = t;
				if (!wa(e, t)) {
					if (Ta(e)) throw Error(r(418));
					t = ki(n.nextSibling);
					var i = xa;
					t && wa(e, t) ? q(i, n) : (e.flags = e.flags & -4097 | 2, K = !1, xa = e);
				}
			} else {
				if (Ta(e)) throw Error(r(418));
				e.flags = e.flags & -4097 | 2, K = !1, xa = e;
			}
		}
	}
	function Da(e) {
		for (e = e.return; e !== null && e.tag !== 5 && e.tag !== 3 && e.tag !== 13;) e = e.return;
		xa = e;
	}
	function Oa(e) {
		if (e !== xa) return !1;
		if (!K) return Da(e), K = !0, !1;
		var t;
		if ((t = e.tag !== 3) && !(t = e.tag !== 5) && (t = e.type, t = t !== "head" && t !== "body" && !Si(e.type, e.memoizedProps)), t &&= Sa) {
			if (Ta(e)) throw ka(), Error(r(418));
			for (; t;) q(e, t), t = ki(t.nextSibling);
		}
		if (Da(e), e.tag === 13) {
			if (e = e.memoizedState, e = e === null ? null : e.dehydrated, !e) throw Error(r(317));
			a: {
				for (e = e.nextSibling, t = 0; e;) {
					if (e.nodeType === 8) {
						var n = e.data;
						if (n === "/$") {
							if (t === 0) {
								Sa = ki(e.nextSibling);
								break a;
							}
							t--;
						} else n !== "$" && n !== "$!" && n !== "$?" || t++;
					}
					e = e.nextSibling;
				}
				Sa = null;
			}
		} else Sa = xa ? ki(e.stateNode.nextSibling) : null;
		return !0;
	}
	function ka() {
		for (var e = Sa; e;) e = ki(e.nextSibling);
	}
	function Aa() {
		Sa = xa = null, K = !1;
	}
	function ja(e) {
		Ca === null ? Ca = [e] : Ca.push(e);
	}
	var Ma = C.ReactCurrentBatchConfig;
	function Na(e, t, n) {
		if (e = n.ref, e !== null && typeof e != "function" && typeof e != "object") {
			if (n._owner) {
				if (n = n._owner, n) {
					if (n.tag !== 1) throw Error(r(309));
					var i = n.stateNode;
				}
				if (!i) throw Error(r(147, e));
				var a = i, o = "" + e;
				return t !== null && t.ref !== null && typeof t.ref == "function" && t.ref._stringRef === o ? t.ref : (t = function(e) {
					var t = a.refs;
					e === null ? delete t[o] : t[o] = e;
				}, t._stringRef = o, t);
			}
			if (typeof e != "string") throw Error(r(284));
			if (!n._owner) throw Error(r(290, e));
		}
		return e;
	}
	function Pa(e, t) {
		throw e = Object.prototype.toString.call(t), Error(r(31, e === "[object Object]" ? "object with keys {" + Object.keys(t).join(", ") + "}" : e));
	}
	function Fa(e) {
		var t = e._init;
		return t(e._payload);
	}
	function Ia(e) {
		function t(t, n) {
			if (e) {
				var r = t.deletions;
				r === null ? (t.deletions = [n], t.flags |= 16) : r.push(n);
			}
		}
		function n(n, r) {
			if (!e) return null;
			for (; r !== null;) t(n, r), r = r.sibling;
			return null;
		}
		function i(e, t) {
			for (e = /* @__PURE__ */ new Map(); t !== null;) t.key === null ? e.set(t.index, t) : e.set(t.key, t), t = t.sibling;
			return e;
		}
		function a(e, t) {
			return e = Yl(e, t), e.index = 0, e.sibling = null, e;
		}
		function o(t, n, r) {
			return t.index = r, e ? (r = t.alternate, r === null ? (t.flags |= 2, n) : (r = r.index, r < n ? (t.flags |= 2, n) : r)) : (t.flags |= 1048576, n);
		}
		function s(t) {
			return e && t.alternate === null && (t.flags |= 2), t;
		}
		function c(e, t, n, r) {
			return t === null || t.tag !== 6 ? (t = $l(n, e.mode, r), t.return = e, t) : (t = a(t, n), t.return = e, t);
		}
		function l(e, t, n, r) {
			var i = n.type;
			return i === E ? d(e, t, n.props.children, r, n.key) : t !== null && (t.elementType === i || typeof i == "object" && i && i.$$typeof === F && Fa(i) === t.type) ? (r = a(t, n.props), r.ref = Na(e, t, n), r.return = e, r) : (r = Xl(n.type, n.key, n.props, null, e.mode, r), r.ref = Na(e, t, n), r.return = e, r);
		}
		function u(e, t, n, r) {
			return t === null || t.tag !== 4 || t.stateNode.containerInfo !== n.containerInfo || t.stateNode.implementation !== n.implementation ? (t = eu(n, e.mode, r), t.return = e, t) : (t = a(t, n.children || []), t.return = e, t);
		}
		function d(e, t, n, r, i) {
			return t === null || t.tag !== 7 ? (t = Zl(n, e.mode, r, i), t.return = e, t) : (t = a(t, n), t.return = e, t);
		}
		function f(e, t, n) {
			if (typeof t == "string" && t !== "" || typeof t == "number") return t = $l("" + t, e.mode, n), t.return = e, t;
			if (typeof t == "object" && t) {
				switch (t.$$typeof) {
					case w: return n = Xl(t.type, t.key, t.props, null, e.mode, n), n.ref = Na(e, null, t), n.return = e, n;
					case T: return t = eu(t, e.mode, n), t.return = e, t;
					case F:
						var r = t._init;
						return f(e, r(t._payload), n);
				}
				if (ve(t) || L(t)) return t = Zl(t, e.mode, n, null), t.return = e, t;
				Pa(e, t);
			}
			return null;
		}
		function p(e, t, n, r) {
			var i = t === null ? null : t.key;
			if (typeof n == "string" && n !== "" || typeof n == "number") return i === null ? c(e, t, "" + n, r) : null;
			if (typeof n == "object" && n) {
				switch (n.$$typeof) {
					case w: return n.key === i ? l(e, t, n, r) : null;
					case T: return n.key === i ? u(e, t, n, r) : null;
					case F: return i = n._init, p(e, t, i(n._payload), r);
				}
				if (ve(n) || L(n)) return i === null ? d(e, t, n, r, null) : null;
				Pa(e, n);
			}
			return null;
		}
		function m(e, t, n, r, i) {
			if (typeof r == "string" && r !== "" || typeof r == "number") return e = e.get(n) || null, c(t, e, "" + r, i);
			if (typeof r == "object" && r) {
				switch (r.$$typeof) {
					case w: return e = e.get(r.key === null ? n : r.key) || null, l(t, e, r, i);
					case T: return e = e.get(r.key === null ? n : r.key) || null, u(t, e, r, i);
					case F:
						var a = r._init;
						return m(e, t, n, a(r._payload), i);
				}
				if (ve(r) || L(r)) return e = e.get(n) || null, d(t, e, r, i, null);
				Pa(t, r);
			}
			return null;
		}
		function h(r, a, s, c) {
			for (var l = null, u = null, d = a, h = a = 0, g = null; d !== null && h < s.length; h++) {
				d.index > h ? (g = d, d = null) : g = d.sibling;
				var _ = p(r, d, s[h], c);
				if (_ === null) {
					d === null && (d = g);
					break;
				}
				e && d && _.alternate === null && t(r, d), a = o(_, a, h), u === null ? l = _ : u.sibling = _, u = _, d = g;
			}
			if (h === s.length) return n(r, d), K && _a(r, h), l;
			if (d === null) {
				for (; h < s.length; h++) d = f(r, s[h], c), d !== null && (a = o(d, a, h), u === null ? l = d : u.sibling = d, u = d);
				return K && _a(r, h), l;
			}
			for (d = i(r, d); h < s.length; h++) g = m(d, r, h, s[h], c), g !== null && (e && g.alternate !== null && d.delete(g.key === null ? h : g.key), a = o(g, a, h), u === null ? l = g : u.sibling = g, u = g);
			return e && d.forEach(function(e) {
				return t(r, e);
			}), K && _a(r, h), l;
		}
		function g(a, s, c, l) {
			var u = L(c);
			if (typeof u != "function") throw Error(r(150));
			if (c = u.call(c), c == null) throw Error(r(151));
			for (var d = u = null, h = s, g = s = 0, _ = null, v = c.next(); h !== null && !v.done; g++, v = c.next()) {
				h.index > g ? (_ = h, h = null) : _ = h.sibling;
				var y = p(a, h, v.value, l);
				if (y === null) {
					h === null && (h = _);
					break;
				}
				e && h && y.alternate === null && t(a, h), s = o(y, s, g), d === null ? u = y : d.sibling = y, d = y, h = _;
			}
			if (v.done) return n(a, h), K && _a(a, g), u;
			if (h === null) {
				for (; !v.done; g++, v = c.next()) v = f(a, v.value, l), v !== null && (s = o(v, s, g), d === null ? u = v : d.sibling = v, d = v);
				return K && _a(a, g), u;
			}
			for (h = i(a, h); !v.done; g++, v = c.next()) v = m(h, a, g, v.value, l), v !== null && (e && v.alternate !== null && h.delete(v.key === null ? g : v.key), s = o(v, s, g), d === null ? u = v : d.sibling = v, d = v);
			return e && h.forEach(function(e) {
				return t(a, e);
			}), K && _a(a, g), u;
		}
		function _(e, r, i, o) {
			if (typeof i == "object" && i && i.type === E && i.key === null && (i = i.props.children), typeof i == "object" && i) {
				switch (i.$$typeof) {
					case w:
						a: {
							for (var c = i.key, l = r; l !== null;) {
								if (l.key === c) {
									if (c = i.type, c === E) {
										if (l.tag === 7) {
											n(e, l.sibling), r = a(l, i.props.children), r.return = e, e = r;
											break a;
										}
									} else if (l.elementType === c || typeof c == "object" && c && c.$$typeof === F && Fa(c) === l.type) {
										n(e, l.sibling), r = a(l, i.props), r.ref = Na(e, l, i), r.return = e, e = r;
										break a;
									}
									n(e, l);
									break;
								} else t(e, l);
								l = l.sibling;
							}
							i.type === E ? (r = Zl(i.props.children, e.mode, o, i.key), r.return = e, e = r) : (o = Xl(i.type, i.key, i.props, null, e.mode, o), o.ref = Na(e, r, i), o.return = e, e = o);
						}
						return s(e);
					case T:
						a: {
							for (l = i.key; r !== null;) {
								if (r.key === l) if (r.tag === 4 && r.stateNode.containerInfo === i.containerInfo && r.stateNode.implementation === i.implementation) {
									n(e, r.sibling), r = a(r, i.children || []), r.return = e, e = r;
									break a;
								} else {
									n(e, r);
									break;
								}
								else t(e, r);
								r = r.sibling;
							}
							r = eu(i, e.mode, o), r.return = e, e = r;
						}
						return s(e);
					case F: return l = i._init, _(e, r, l(i._payload), o);
				}
				if (ve(i)) return h(e, r, i, o);
				if (L(i)) return g(e, r, i, o);
				Pa(e, i);
			}
			return typeof i == "string" && i !== "" || typeof i == "number" ? (i = "" + i, r !== null && r.tag === 6 ? (n(e, r.sibling), r = a(r, i), r.return = e, e = r) : (n(e, r), r = $l(i, e.mode, o), r.return = e, e = r), s(e)) : n(e, r);
		}
		return _;
	}
	var La = Ia(!0), Ra = Ia(!1), za = Wi(null), Ba = null, Va = null, Ha = null;
	function Ua() {
		Ha = Va = Ba = null;
	}
	function Wa(e) {
		var t = za.current;
		W(za), e._currentValue = t;
	}
	function Ga(e, t, n) {
		for (; e !== null;) {
			var r = e.alternate;
			if ((e.childLanes & t) === t ? r !== null && (r.childLanes & t) !== t && (r.childLanes |= t) : (e.childLanes |= t, r !== null && (r.childLanes |= t)), e === n) break;
			e = e.return;
		}
	}
	function Ka(e, t) {
		Ba = e, Ha = Va = null, e = e.dependencies, e !== null && e.firstContext !== null && ((e.lanes & t) !== 0 && (Fs = !0), e.firstContext = null);
	}
	function qa(e) {
		var t = e._currentValue;
		if (Ha !== e) if (e = {
			context: e,
			memoizedValue: t,
			next: null
		}, Va === null) {
			if (Ba === null) throw Error(r(308));
			Va = e, Ba.dependencies = {
				lanes: 0,
				firstContext: e
			};
		} else Va = Va.next = e;
		return t;
	}
	var Ja = null;
	function Ya(e) {
		Ja === null ? Ja = [e] : Ja.push(e);
	}
	function Xa(e, t, n, r) {
		var i = t.interleaved;
		return i === null ? (n.next = n, Ya(t)) : (n.next = i.next, i.next = n), t.interleaved = n, Za(e, r);
	}
	function Za(e, t) {
		e.lanes |= t;
		var n = e.alternate;
		for (n !== null && (n.lanes |= t), n = e, e = e.return; e !== null;) e.childLanes |= t, n = e.alternate, n !== null && (n.childLanes |= t), n = e, e = e.return;
		return n.tag === 3 ? n.stateNode : null;
	}
	var Qa = !1;
	function $a(e) {
		e.updateQueue = {
			baseState: e.memoizedState,
			firstBaseUpdate: null,
			lastBaseUpdate: null,
			shared: {
				pending: null,
				interleaved: null,
				lanes: 0
			},
			effects: null
		};
	}
	function eo(e, t) {
		e = e.updateQueue, t.updateQueue === e && (t.updateQueue = {
			baseState: e.baseState,
			firstBaseUpdate: e.firstBaseUpdate,
			lastBaseUpdate: e.lastBaseUpdate,
			shared: e.shared,
			effects: e.effects
		});
	}
	function to(e, t) {
		return {
			eventTime: e,
			lane: t,
			tag: 0,
			payload: null,
			callback: null,
			next: null
		};
	}
	function no(e, t, n) {
		var r = e.updateQueue;
		if (r === null) return null;
		if (r = r.shared, $ & 2) {
			var i = r.pending;
			return i === null ? t.next = t : (t.next = i.next, i.next = t), r.pending = t, Za(e, n);
		}
		return i = r.interleaved, i === null ? (t.next = t, Ya(r)) : (t.next = i.next, i.next = t), r.interleaved = t, Za(e, n);
	}
	function ro(e, t, n) {
		if (t = t.updateQueue, t !== null && (t = t.shared, n & 4194240)) {
			var r = t.lanes;
			r &= e.pendingLanes, n |= r, t.lanes = n, Bt(e, n);
		}
	}
	function io(e, t) {
		var n = e.updateQueue, r = e.alternate;
		if (r !== null && (r = r.updateQueue, n === r)) {
			var i = null, a = null;
			if (n = n.firstBaseUpdate, n !== null) {
				do {
					var o = {
						eventTime: n.eventTime,
						lane: n.lane,
						tag: n.tag,
						payload: n.payload,
						callback: n.callback,
						next: null
					};
					a === null ? i = a = o : a = a.next = o, n = n.next;
				} while (n !== null);
				a === null ? i = a = t : a = a.next = t;
			} else i = a = t;
			n = {
				baseState: r.baseState,
				firstBaseUpdate: i,
				lastBaseUpdate: a,
				shared: r.shared,
				effects: r.effects
			}, e.updateQueue = n;
			return;
		}
		e = n.lastBaseUpdate, e === null ? n.firstBaseUpdate = t : e.next = t, n.lastBaseUpdate = t;
	}
	function ao(e, t, n, r) {
		var i = e.updateQueue;
		Qa = !1;
		var a = i.firstBaseUpdate, o = i.lastBaseUpdate, s = i.shared.pending;
		if (s !== null) {
			i.shared.pending = null;
			var c = s, l = c.next;
			c.next = null, o === null ? a = l : o.next = l, o = c;
			var u = e.alternate;
			u !== null && (u = u.updateQueue, s = u.lastBaseUpdate, s !== o && (s === null ? u.firstBaseUpdate = l : s.next = l, u.lastBaseUpdate = c));
		}
		if (a !== null) {
			var d = i.baseState;
			o = 0, u = l = c = null, s = a;
			do {
				var f = s.lane, p = s.eventTime;
				if ((r & f) === f) {
					u !== null && (u = u.next = {
						eventTime: p,
						lane: 0,
						tag: s.tag,
						payload: s.payload,
						callback: s.callback,
						next: null
					});
					a: {
						var m = e, h = s;
						switch (f = t, p = n, h.tag) {
							case 1:
								if (m = h.payload, typeof m == "function") {
									d = m.call(p, d, f);
									break a;
								}
								d = m;
								break a;
							case 3: m.flags = m.flags & -65537 | 128;
							case 0:
								if (m = h.payload, f = typeof m == "function" ? m.call(p, d, f) : m, f == null) break a;
								d = R({}, d, f);
								break a;
							case 2: Qa = !0;
						}
					}
					s.callback !== null && s.lane !== 0 && (e.flags |= 64, f = i.effects, f === null ? i.effects = [s] : f.push(s));
				} else p = {
					eventTime: p,
					lane: f,
					tag: s.tag,
					payload: s.payload,
					callback: s.callback,
					next: null
				}, u === null ? (l = u = p, c = d) : u = u.next = p, o |= f;
				if (s = s.next, s === null) {
					if (s = i.shared.pending, s === null) break;
					f = s, s = f.next, f.next = null, i.lastBaseUpdate = f, i.shared.pending = null;
				}
			} while (1);
			if (u === null && (c = d), i.baseState = c, i.firstBaseUpdate = l, i.lastBaseUpdate = u, t = i.shared.interleaved, t !== null) {
				i = t;
				do
					o |= i.lane, i = i.next;
				while (i !== t);
			} else a === null && (i.shared.lanes = 0);
			Jc |= o, e.lanes = o, e.memoizedState = d;
		}
	}
	function oo(e, t, n) {
		if (e = t.effects, t.effects = null, e !== null) for (t = 0; t < e.length; t++) {
			var i = e[t], a = i.callback;
			if (a !== null) {
				if (i.callback = null, i = n, typeof a != "function") throw Error(r(191, a));
				a.call(i);
			}
		}
	}
	var so = {}, co = Wi(so), lo = Wi(so), uo = Wi(so);
	function fo(e) {
		if (e === so) throw Error(r(174));
		return e;
	}
	function po(e, t) {
		switch (G(uo, t), G(lo, e), G(co, so), e = t.nodeType, e) {
			case 9:
			case 11:
				t = (t = t.documentElement) ? t.namespaceURI : Te(null, "");
				break;
			default: e = e === 8 ? t.parentNode : t, t = e.namespaceURI || null, e = e.tagName, t = Te(t, e);
		}
		W(co), G(co, t);
	}
	function mo() {
		W(co), W(lo), W(uo);
	}
	function ho(e) {
		fo(uo.current);
		var t = fo(co.current), n = Te(t, e.type);
		t !== n && (G(lo, e), G(co, n));
	}
	function go(e) {
		lo.current === e && (W(co), W(lo));
	}
	var J = Wi(0);
	function _o(e) {
		for (var t = e; t !== null;) {
			if (t.tag === 13) {
				var n = t.memoizedState;
				if (n !== null && (n = n.dehydrated, n === null || n.data === "$?" || n.data === "$!")) return t;
			} else if (t.tag === 19 && t.memoizedProps.revealOrder !== void 0) {
				if (t.flags & 128) return t;
			} else if (t.child !== null) {
				t.child.return = t, t = t.child;
				continue;
			}
			if (t === e) break;
			for (; t.sibling === null;) {
				if (t.return === null || t.return === e) return null;
				t = t.return;
			}
			t.sibling.return = t.return, t = t.sibling;
		}
		return null;
	}
	var vo = [];
	function yo() {
		for (var e = 0; e < vo.length; e++) vo[e]._workInProgressVersionPrimary = null;
		vo.length = 0;
	}
	var bo = C.ReactCurrentDispatcher, xo = C.ReactCurrentBatchConfig, So = 0, Co = null, wo = null, To = null, Eo = !1, Do = !1, Oo = 0, ko = 0;
	function Ao() {
		throw Error(r(321));
	}
	function jo(e, t) {
		if (t === null) return !1;
		for (var n = 0; n < t.length && n < e.length; n++) if (!Or(e[n], t[n])) return !1;
		return !0;
	}
	function Mo(e, t, n, i, a, o) {
		if (So = o, Co = t, t.memoizedState = null, t.updateQueue = null, t.lanes = 0, bo.current = e === null || e.memoizedState === null ? hs : gs, e = n(i, a), Do) {
			o = 0;
			do {
				if (Do = !1, Oo = 0, 25 <= o) throw Error(r(301));
				o += 1, To = wo = null, t.updateQueue = null, bo.current = _s, e = n(i, a);
			} while (Do);
		}
		if (bo.current = ms, t = wo !== null && wo.next !== null, So = 0, To = wo = Co = null, Eo = !1, t) throw Error(r(300));
		return e;
	}
	function No() {
		var e = Oo !== 0;
		return Oo = 0, e;
	}
	function Po() {
		var e = {
			memoizedState: null,
			baseState: null,
			baseQueue: null,
			queue: null,
			next: null
		};
		return To === null ? Co.memoizedState = To = e : To = To.next = e, To;
	}
	function Fo() {
		if (wo === null) {
			var e = Co.alternate;
			e = e === null ? null : e.memoizedState;
		} else e = wo.next;
		var t = To === null ? Co.memoizedState : To.next;
		if (t !== null) To = t, wo = e;
		else {
			if (e === null) throw Error(r(310));
			wo = e, e = {
				memoizedState: wo.memoizedState,
				baseState: wo.baseState,
				baseQueue: wo.baseQueue,
				queue: wo.queue,
				next: null
			}, To === null ? Co.memoizedState = To = e : To = To.next = e;
		}
		return To;
	}
	function Io(e, t) {
		return typeof t == "function" ? t(e) : t;
	}
	function Lo(e) {
		var t = Fo(), n = t.queue;
		if (n === null) throw Error(r(311));
		n.lastRenderedReducer = e;
		var i = wo, a = i.baseQueue, o = n.pending;
		if (o !== null) {
			if (a !== null) {
				var s = a.next;
				a.next = o.next, o.next = s;
			}
			i.baseQueue = a = o, n.pending = null;
		}
		if (a !== null) {
			o = a.next, i = i.baseState;
			var c = s = null, l = null, u = o;
			do {
				var d = u.lane;
				if ((So & d) === d) l !== null && (l = l.next = {
					lane: 0,
					action: u.action,
					hasEagerState: u.hasEagerState,
					eagerState: u.eagerState,
					next: null
				}), i = u.hasEagerState ? u.eagerState : e(i, u.action);
				else {
					var f = {
						lane: d,
						action: u.action,
						hasEagerState: u.hasEagerState,
						eagerState: u.eagerState,
						next: null
					};
					l === null ? (c = l = f, s = i) : l = l.next = f, Co.lanes |= d, Jc |= d;
				}
				u = u.next;
			} while (u !== null && u !== o);
			l === null ? s = i : l.next = c, Or(i, t.memoizedState) || (Fs = !0), t.memoizedState = i, t.baseState = s, t.baseQueue = l, n.lastRenderedState = i;
		}
		if (e = n.interleaved, e !== null) {
			a = e;
			do
				o = a.lane, Co.lanes |= o, Jc |= o, a = a.next;
			while (a !== e);
		} else a === null && (n.lanes = 0);
		return [t.memoizedState, n.dispatch];
	}
	function Ro(e) {
		var t = Fo(), n = t.queue;
		if (n === null) throw Error(r(311));
		n.lastRenderedReducer = e;
		var i = n.dispatch, a = n.pending, o = t.memoizedState;
		if (a !== null) {
			n.pending = null;
			var s = a = a.next;
			do
				o = e(o, s.action), s = s.next;
			while (s !== a);
			Or(o, t.memoizedState) || (Fs = !0), t.memoizedState = o, t.baseQueue === null && (t.baseState = o), n.lastRenderedState = o;
		}
		return [o, i];
	}
	function zo() {}
	function Bo(e, t) {
		var n = Co, i = Fo(), a = t(), o = !Or(i.memoizedState, a);
		if (o && (i.memoizedState = a, Fs = !0), i = i.queue, Qo(Uo.bind(null, n, i, e), [e]), i.getSnapshot !== t || o || To !== null && To.memoizedState.tag & 1) {
			if (n.flags |= 2048, qo(9, Ho.bind(null, n, i, a, t), void 0, null), Vc === null) throw Error(r(349));
			So & 30 || Vo(n, t, a);
		}
		return a;
	}
	function Vo(e, t, n) {
		e.flags |= 16384, e = {
			getSnapshot: t,
			value: n
		}, t = Co.updateQueue, t === null ? (t = {
			lastEffect: null,
			stores: null
		}, Co.updateQueue = t, t.stores = [e]) : (n = t.stores, n === null ? t.stores = [e] : n.push(e));
	}
	function Ho(e, t, n, r) {
		t.value = n, t.getSnapshot = r, Wo(t) && Go(e);
	}
	function Uo(e, t, n) {
		return n(function() {
			Wo(t) && Go(e);
		});
	}
	function Wo(e) {
		var t = e.getSnapshot;
		e = e.value;
		try {
			var n = t();
			return !Or(e, n);
		} catch {
			return !0;
		}
	}
	function Go(e) {
		var t = Za(e, 1);
		t !== null && ml(t, e, 1, -1);
	}
	function Ko(e) {
		var t = Po();
		return typeof e == "function" && (e = e()), t.memoizedState = t.baseState = e, e = {
			pending: null,
			interleaved: null,
			lanes: 0,
			dispatch: null,
			lastRenderedReducer: Io,
			lastRenderedState: e
		}, t.queue = e, e = e.dispatch = us.bind(null, Co, e), [t.memoizedState, e];
	}
	function qo(e, t, n, r) {
		return e = {
			tag: e,
			create: t,
			destroy: n,
			deps: r,
			next: null
		}, t = Co.updateQueue, t === null ? (t = {
			lastEffect: null,
			stores: null
		}, Co.updateQueue = t, t.lastEffect = e.next = e) : (n = t.lastEffect, n === null ? t.lastEffect = e.next = e : (r = n.next, n.next = e, e.next = r, t.lastEffect = e)), e;
	}
	function Jo() {
		return Fo().memoizedState;
	}
	function Yo(e, t, n, r) {
		var i = Po();
		Co.flags |= e, i.memoizedState = qo(1 | t, n, void 0, r === void 0 ? null : r);
	}
	function Xo(e, t, n, r) {
		var i = Fo();
		r = r === void 0 ? null : r;
		var a = void 0;
		if (wo !== null) {
			var o = wo.memoizedState;
			if (a = o.destroy, r !== null && jo(r, o.deps)) {
				i.memoizedState = qo(t, n, a, r);
				return;
			}
		}
		Co.flags |= e, i.memoizedState = qo(1 | t, n, a, r);
	}
	function Zo(e, t) {
		return Yo(8390656, 8, e, t);
	}
	function Qo(e, t) {
		return Xo(2048, 8, e, t);
	}
	function $o(e, t) {
		return Xo(4, 2, e, t);
	}
	function es(e, t) {
		return Xo(4, 4, e, t);
	}
	function ts(e, t) {
		if (typeof t == "function") return e = e(), t(e), function() {
			t(null);
		};
		if (t != null) return e = e(), t.current = e, function() {
			t.current = null;
		};
	}
	function ns(e, t, n) {
		return n = n == null ? null : n.concat([e]), Xo(4, 4, ts.bind(null, t, e), n);
	}
	function rs() {}
	function is(e, t) {
		var n = Fo();
		t = t === void 0 ? null : t;
		var r = n.memoizedState;
		return r !== null && t !== null && jo(t, r[1]) ? r[0] : (n.memoizedState = [e, t], e);
	}
	function as(e, t) {
		var n = Fo();
		t = t === void 0 ? null : t;
		var r = n.memoizedState;
		return r !== null && t !== null && jo(t, r[1]) ? r[0] : (e = e(), n.memoizedState = [e, t], e);
	}
	function os(e, t, n) {
		return So & 21 ? (Or(n, t) || (n = It(), Co.lanes |= n, Jc |= n, e.baseState = !0), t) : (e.baseState && (e.baseState = !1, Fs = !0), e.memoizedState = n);
	}
	function ss(e, t) {
		var n = V;
		V = n !== 0 && 4 > n ? n : 4, e(!0);
		var r = xo.transition;
		xo.transition = {};
		try {
			e(!1), t();
		} finally {
			V = n, xo.transition = r;
		}
	}
	function cs() {
		return Fo().memoizedState;
	}
	function ls(e, t, n) {
		var r = pl(e);
		if (n = {
			lane: r,
			action: n,
			hasEagerState: !1,
			eagerState: null,
			next: null
		}, ds(e)) fs(t, n);
		else if (n = Xa(e, t, n, r), n !== null) {
			var i = fl();
			ml(n, e, r, i), ps(n, t, r);
		}
	}
	function us(e, t, n) {
		var r = pl(e), i = {
			lane: r,
			action: n,
			hasEagerState: !1,
			eagerState: null,
			next: null
		};
		if (ds(e)) fs(t, i);
		else {
			var a = e.alternate;
			if (e.lanes === 0 && (a === null || a.lanes === 0) && (a = t.lastRenderedReducer, a !== null)) try {
				var o = t.lastRenderedState, s = a(o, n);
				if (i.hasEagerState = !0, i.eagerState = s, Or(s, o)) {
					var c = t.interleaved;
					c === null ? (i.next = i, Ya(t)) : (i.next = c.next, c.next = i), t.interleaved = i;
					return;
				}
			} catch {}
			n = Xa(e, t, i, r), n !== null && (i = fl(), ml(n, e, r, i), ps(n, t, r));
		}
	}
	function ds(e) {
		var t = e.alternate;
		return e === Co || t !== null && t === Co;
	}
	function fs(e, t) {
		Do = Eo = !0;
		var n = e.pending;
		n === null ? t.next = t : (t.next = n.next, n.next = t), e.pending = t;
	}
	function ps(e, t, n) {
		if (n & 4194240) {
			var r = t.lanes;
			r &= e.pendingLanes, n |= r, t.lanes = n, Bt(e, n);
		}
	}
	var ms = {
		readContext: qa,
		useCallback: Ao,
		useContext: Ao,
		useEffect: Ao,
		useImperativeHandle: Ao,
		useInsertionEffect: Ao,
		useLayoutEffect: Ao,
		useMemo: Ao,
		useReducer: Ao,
		useRef: Ao,
		useState: Ao,
		useDebugValue: Ao,
		useDeferredValue: Ao,
		useTransition: Ao,
		useMutableSource: Ao,
		useSyncExternalStore: Ao,
		useId: Ao,
		unstable_isNewReconciler: !1
	}, hs = {
		readContext: qa,
		useCallback: function(e, t) {
			return Po().memoizedState = [e, t === void 0 ? null : t], e;
		},
		useContext: qa,
		useEffect: Zo,
		useImperativeHandle: function(e, t, n) {
			return n = n == null ? null : n.concat([e]), Yo(4194308, 4, ts.bind(null, t, e), n);
		},
		useLayoutEffect: function(e, t) {
			return Yo(4194308, 4, e, t);
		},
		useInsertionEffect: function(e, t) {
			return Yo(4, 2, e, t);
		},
		useMemo: function(e, t) {
			var n = Po();
			return t = t === void 0 ? null : t, e = e(), n.memoizedState = [e, t], e;
		},
		useReducer: function(e, t, n) {
			var r = Po();
			return t = n === void 0 ? t : n(t), r.memoizedState = r.baseState = t, e = {
				pending: null,
				interleaved: null,
				lanes: 0,
				dispatch: null,
				lastRenderedReducer: e,
				lastRenderedState: t
			}, r.queue = e, e = e.dispatch = ls.bind(null, Co, e), [r.memoizedState, e];
		},
		useRef: function(e) {
			var t = Po();
			return e = { current: e }, t.memoizedState = e;
		},
		useState: Ko,
		useDebugValue: rs,
		useDeferredValue: function(e) {
			return Po().memoizedState = e;
		},
		useTransition: function() {
			var e = Ko(!1), t = e[0];
			return e = ss.bind(null, e[1]), Po().memoizedState = e, [t, e];
		},
		useMutableSource: function() {},
		useSyncExternalStore: function(e, t, n) {
			var i = Co, a = Po();
			if (K) {
				if (n === void 0) throw Error(r(407));
				n = n();
			} else {
				if (n = t(), Vc === null) throw Error(r(349));
				So & 30 || Vo(i, t, n);
			}
			a.memoizedState = n;
			var o = {
				value: n,
				getSnapshot: t
			};
			return a.queue = o, Zo(Uo.bind(null, i, o, e), [e]), i.flags |= 2048, qo(9, Ho.bind(null, i, o, n, t), void 0, null), n;
		},
		useId: function() {
			var e = Po(), t = Vc.identifierPrefix;
			if (K) {
				var n = ga, r = ha;
				n = (r & ~(1 << 32 - Tt(r) - 1)).toString(32) + n, t = ":" + t + "R" + n, n = Oo++, 0 < n && (t += "H" + n.toString(32)), t += ":";
			} else n = ko++, t = ":" + t + "r" + n.toString(32) + ":";
			return e.memoizedState = t;
		},
		unstable_isNewReconciler: !1
	}, gs = {
		readContext: qa,
		useCallback: is,
		useContext: qa,
		useEffect: Qo,
		useImperativeHandle: ns,
		useInsertionEffect: $o,
		useLayoutEffect: es,
		useMemo: as,
		useReducer: Lo,
		useRef: Jo,
		useState: function() {
			return Lo(Io);
		},
		useDebugValue: rs,
		useDeferredValue: function(e) {
			return os(Fo(), wo.memoizedState, e);
		},
		useTransition: function() {
			return [Lo(Io)[0], Fo().memoizedState];
		},
		useMutableSource: zo,
		useSyncExternalStore: Bo,
		useId: cs,
		unstable_isNewReconciler: !1
	}, _s = {
		readContext: qa,
		useCallback: is,
		useContext: qa,
		useEffect: Qo,
		useImperativeHandle: ns,
		useInsertionEffect: $o,
		useLayoutEffect: es,
		useMemo: as,
		useReducer: Ro,
		useRef: Jo,
		useState: function() {
			return Ro(Io);
		},
		useDebugValue: rs,
		useDeferredValue: function(e) {
			var t = Fo();
			return wo === null ? t.memoizedState = e : os(t, wo.memoizedState, e);
		},
		useTransition: function() {
			return [Ro(Io)[0], Fo().memoizedState];
		},
		useMutableSource: zo,
		useSyncExternalStore: Bo,
		useId: cs,
		unstable_isNewReconciler: !1
	};
	function vs(e, t) {
		if (e && e.defaultProps) {
			for (var n in t = R({}, t), e = e.defaultProps, e) t[n] === void 0 && (t[n] = e[n]);
			return t;
		}
		return t;
	}
	function ys(e, t, n, r) {
		t = e.memoizedState, n = n(r, t), n = n == null ? t : R({}, t, n), e.memoizedState = n, e.lanes === 0 && (e.updateQueue.baseState = n);
	}
	var bs = {
		isMounted: function(e) {
			return (e = e._reactInternals) ? at(e) === e : !1;
		},
		enqueueSetState: function(e, t, n) {
			e = e._reactInternals;
			var r = fl(), i = pl(e), a = to(r, i);
			a.payload = t, n != null && (a.callback = n), t = no(e, a, i), t !== null && (ml(t, e, i, r), ro(t, e, i));
		},
		enqueueReplaceState: function(e, t, n) {
			e = e._reactInternals;
			var r = fl(), i = pl(e), a = to(r, i);
			a.tag = 1, a.payload = t, n != null && (a.callback = n), t = no(e, a, i), t !== null && (ml(t, e, i, r), ro(t, e, i));
		},
		enqueueForceUpdate: function(e, t) {
			e = e._reactInternals;
			var n = fl(), r = pl(e), i = to(n, r);
			i.tag = 2, t != null && (i.callback = t), t = no(e, i, r), t !== null && (ml(t, e, r, n), ro(t, e, r));
		}
	};
	function xs(e, t, n, r, i, a, o) {
		return e = e.stateNode, typeof e.shouldComponentUpdate == "function" ? e.shouldComponentUpdate(r, a, o) : t.prototype && t.prototype.isPureReactComponent ? !kr(n, r) || !kr(i, a) : !0;
	}
	function Ss(e, t, n) {
		var r = !1, i = Gi, a = t.contextType;
		return typeof a == "object" && a ? a = qa(a) : (i = Xi(t) ? Ji : Ki.current, r = t.contextTypes, a = (r = r != null) ? Yi(e, i) : Gi), t = new t(n, a), e.memoizedState = t.state !== null && t.state !== void 0 ? t.state : null, t.updater = bs, e.stateNode = t, t._reactInternals = e, r && (e = e.stateNode, e.__reactInternalMemoizedUnmaskedChildContext = i, e.__reactInternalMemoizedMaskedChildContext = a), t;
	}
	function Cs(e, t, n, r) {
		e = t.state, typeof t.componentWillReceiveProps == "function" && t.componentWillReceiveProps(n, r), typeof t.UNSAFE_componentWillReceiveProps == "function" && t.UNSAFE_componentWillReceiveProps(n, r), t.state !== e && bs.enqueueReplaceState(t, t.state, null);
	}
	function ws(e, t, n, r) {
		var i = e.stateNode;
		i.props = n, i.state = e.memoizedState, i.refs = {}, $a(e);
		var a = t.contextType;
		typeof a == "object" && a ? i.context = qa(a) : (a = Xi(t) ? Ji : Ki.current, i.context = Yi(e, a)), i.state = e.memoizedState, a = t.getDerivedStateFromProps, typeof a == "function" && (ys(e, t, a, n), i.state = e.memoizedState), typeof t.getDerivedStateFromProps == "function" || typeof i.getSnapshotBeforeUpdate == "function" || typeof i.UNSAFE_componentWillMount != "function" && typeof i.componentWillMount != "function" || (t = i.state, typeof i.componentWillMount == "function" && i.componentWillMount(), typeof i.UNSAFE_componentWillMount == "function" && i.UNSAFE_componentWillMount(), t !== i.state && bs.enqueueReplaceState(i, i.state, null), ao(e, n, i, r), i.state = e.memoizedState), typeof i.componentDidMount == "function" && (e.flags |= 4194308);
	}
	function Ts(e, t) {
		try {
			var n = "", r = t;
			do
				n += re(r), r = r.return;
			while (r);
			var i = n;
		} catch (e) {
			i = "\nError generating stack: " + e.message + "\n" + e.stack;
		}
		return {
			value: e,
			source: t,
			stack: i,
			digest: null
		};
	}
	function Es(e, t, n) {
		return {
			value: e,
			source: null,
			stack: n ?? null,
			digest: t ?? null
		};
	}
	function Ds(e, t) {
		try {
			console.error(t.value);
		} catch (e) {
			setTimeout(function() {
				throw e;
			});
		}
	}
	var Os = typeof WeakMap == "function" ? WeakMap : Map;
	function ks(e, t, n) {
		n = to(-1, n), n.tag = 3, n.payload = { element: null };
		var r = t.value;
		return n.callback = function() {
			nl || (nl = !0, rl = r), Ds(e, t);
		}, n;
	}
	function As(e, t, n) {
		n = to(-1, n), n.tag = 3;
		var r = e.type.getDerivedStateFromError;
		if (typeof r == "function") {
			var i = t.value;
			n.payload = function() {
				return r(i);
			}, n.callback = function() {
				Ds(e, t);
			};
		}
		var a = e.stateNode;
		return a !== null && typeof a.componentDidCatch == "function" && (n.callback = function() {
			Ds(e, t), typeof r != "function" && (il === null ? il = /* @__PURE__ */ new Set([this]) : il.add(this));
			var n = t.stack;
			this.componentDidCatch(t.value, { componentStack: n === null ? "" : n });
		}), n;
	}
	function js(e, t, n) {
		var r = e.pingCache;
		if (r === null) {
			r = e.pingCache = new Os();
			var i = /* @__PURE__ */ new Set();
			r.set(t, i);
		} else i = r.get(t), i === void 0 && (i = /* @__PURE__ */ new Set(), r.set(t, i));
		i.has(n) || (i.add(n), e = zl.bind(null, e, t, n), t.then(e, e));
	}
	function Ms(e) {
		do {
			var t;
			if ((t = e.tag === 13) && (t = e.memoizedState, t = t === null || t.dehydrated !== null), t) return e;
			e = e.return;
		} while (e !== null);
		return null;
	}
	function Ns(e, t, n, r, i) {
		return e.mode & 1 ? (e.flags |= 65536, e.lanes = i, e) : (e === t ? e.flags |= 65536 : (e.flags |= 128, n.flags |= 131072, n.flags &= -52805, n.tag === 1 && (n.alternate === null ? n.tag = 17 : (t = to(-1, 1), t.tag = 2, no(n, t, 1))), n.lanes |= 1), e);
	}
	var Ps = C.ReactCurrentOwner, Fs = !1;
	function Is(e, t, n, r) {
		t.child = e === null ? Ra(t, null, n, r) : La(t, e.child, n, r);
	}
	function Ls(e, t, n, r, i) {
		n = n.render;
		var a = t.ref;
		return Ka(t, i), r = Mo(e, t, n, r, a, i), n = No(), e !== null && !Fs ? (t.updateQueue = e.updateQueue, t.flags &= -2053, e.lanes &= ~i, rc(e, t, i)) : (K && n && ya(t), t.flags |= 1, Is(e, t, r, i), t.child);
	}
	function Rs(e, t, n, r, i) {
		if (e === null) {
			var a = n.type;
			return typeof a == "function" && !ql(a) && a.defaultProps === void 0 && n.compare === null && n.defaultProps === void 0 ? (t.tag = 15, t.type = a, zs(e, t, a, r, i)) : (e = Xl(n.type, null, r, t, t.mode, i), e.ref = t.ref, e.return = t, t.child = e);
		}
		if (a = e.child, (e.lanes & i) === 0) {
			var o = a.memoizedProps;
			if (n = n.compare, n = n === null ? kr : n, n(o, r) && e.ref === t.ref) return rc(e, t, i);
		}
		return t.flags |= 1, e = Yl(a, r), e.ref = t.ref, e.return = t, t.child = e;
	}
	function zs(e, t, n, r, i) {
		if (e !== null) {
			var a = e.memoizedProps;
			if (kr(a, r) && e.ref === t.ref) if (Fs = !1, t.pendingProps = r = a, (e.lanes & i) !== 0) e.flags & 131072 && (Fs = !0);
			else return t.lanes = e.lanes, rc(e, t, i);
		}
		return Hs(e, t, n, r, i);
	}
	function Bs(e, t, n) {
		var r = t.pendingProps, i = r.children, a = e === null ? null : e.memoizedState;
		if (r.mode === "hidden") if (!(t.mode & 1)) t.memoizedState = {
			baseLanes: 0,
			cachePool: null,
			transitions: null
		}, G(Gc, Wc), Wc |= n;
		else {
			if (!(n & 1073741824)) return e = a === null ? n : a.baseLanes | n, t.lanes = t.childLanes = 1073741824, t.memoizedState = {
				baseLanes: e,
				cachePool: null,
				transitions: null
			}, t.updateQueue = null, G(Gc, Wc), Wc |= e, null;
			t.memoizedState = {
				baseLanes: 0,
				cachePool: null,
				transitions: null
			}, r = a === null ? n : a.baseLanes, G(Gc, Wc), Wc |= r;
		}
		else a === null ? r = n : (r = a.baseLanes | n, t.memoizedState = null), G(Gc, Wc), Wc |= r;
		return Is(e, t, i, n), t.child;
	}
	function Vs(e, t) {
		var n = t.ref;
		(e === null && n !== null || e !== null && e.ref !== n) && (t.flags |= 512, t.flags |= 2097152);
	}
	function Hs(e, t, n, r, i) {
		var a = Xi(n) ? Ji : Ki.current;
		return a = Yi(t, a), Ka(t, i), n = Mo(e, t, n, r, a, i), r = No(), e !== null && !Fs ? (t.updateQueue = e.updateQueue, t.flags &= -2053, e.lanes &= ~i, rc(e, t, i)) : (K && r && ya(t), t.flags |= 1, Is(e, t, n, i), t.child);
	}
	function Us(e, t, n, r, i) {
		if (Xi(n)) {
			var a = !0;
			ea(t);
		} else a = !1;
		if (Ka(t, i), t.stateNode === null) nc(e, t), Ss(t, n, r), ws(t, n, r, i), r = !0;
		else if (e === null) {
			var o = t.stateNode, s = t.memoizedProps;
			o.props = s;
			var c = o.context, l = n.contextType;
			typeof l == "object" && l ? l = qa(l) : (l = Xi(n) ? Ji : Ki.current, l = Yi(t, l));
			var u = n.getDerivedStateFromProps, d = typeof u == "function" || typeof o.getSnapshotBeforeUpdate == "function";
			d || typeof o.UNSAFE_componentWillReceiveProps != "function" && typeof o.componentWillReceiveProps != "function" || (s !== r || c !== l) && Cs(t, o, r, l), Qa = !1;
			var f = t.memoizedState;
			o.state = f, ao(t, r, o, i), c = t.memoizedState, s !== r || f !== c || qi.current || Qa ? (typeof u == "function" && (ys(t, n, u, r), c = t.memoizedState), (s = Qa || xs(t, n, s, r, f, c, l)) ? (d || typeof o.UNSAFE_componentWillMount != "function" && typeof o.componentWillMount != "function" || (typeof o.componentWillMount == "function" && o.componentWillMount(), typeof o.UNSAFE_componentWillMount == "function" && o.UNSAFE_componentWillMount()), typeof o.componentDidMount == "function" && (t.flags |= 4194308)) : (typeof o.componentDidMount == "function" && (t.flags |= 4194308), t.memoizedProps = r, t.memoizedState = c), o.props = r, o.state = c, o.context = l, r = s) : (typeof o.componentDidMount == "function" && (t.flags |= 4194308), r = !1);
		} else {
			o = t.stateNode, eo(e, t), s = t.memoizedProps, l = t.type === t.elementType ? s : vs(t.type, s), o.props = l, d = t.pendingProps, f = o.context, c = n.contextType, typeof c == "object" && c ? c = qa(c) : (c = Xi(n) ? Ji : Ki.current, c = Yi(t, c));
			var p = n.getDerivedStateFromProps;
			(u = typeof p == "function" || typeof o.getSnapshotBeforeUpdate == "function") || typeof o.UNSAFE_componentWillReceiveProps != "function" && typeof o.componentWillReceiveProps != "function" || (s !== d || f !== c) && Cs(t, o, r, c), Qa = !1, f = t.memoizedState, o.state = f, ao(t, r, o, i);
			var m = t.memoizedState;
			s !== d || f !== m || qi.current || Qa ? (typeof p == "function" && (ys(t, n, p, r), m = t.memoizedState), (l = Qa || xs(t, n, l, r, f, m, c) || !1) ? (u || typeof o.UNSAFE_componentWillUpdate != "function" && typeof o.componentWillUpdate != "function" || (typeof o.componentWillUpdate == "function" && o.componentWillUpdate(r, m, c), typeof o.UNSAFE_componentWillUpdate == "function" && o.UNSAFE_componentWillUpdate(r, m, c)), typeof o.componentDidUpdate == "function" && (t.flags |= 4), typeof o.getSnapshotBeforeUpdate == "function" && (t.flags |= 1024)) : (typeof o.componentDidUpdate != "function" || s === e.memoizedProps && f === e.memoizedState || (t.flags |= 4), typeof o.getSnapshotBeforeUpdate != "function" || s === e.memoizedProps && f === e.memoizedState || (t.flags |= 1024), t.memoizedProps = r, t.memoizedState = m), o.props = r, o.state = m, o.context = c, r = l) : (typeof o.componentDidUpdate != "function" || s === e.memoizedProps && f === e.memoizedState || (t.flags |= 4), typeof o.getSnapshotBeforeUpdate != "function" || s === e.memoizedProps && f === e.memoizedState || (t.flags |= 1024), r = !1);
		}
		return Ws(e, t, n, r, a, i);
	}
	function Ws(e, t, n, r, i, a) {
		Vs(e, t);
		var o = (t.flags & 128) != 0;
		if (!r && !o) return i && ta(t, n, !1), rc(e, t, a);
		r = t.stateNode, Ps.current = t;
		var s = o && typeof n.getDerivedStateFromError != "function" ? null : r.render();
		return t.flags |= 1, e !== null && o ? (t.child = La(t, e.child, null, a), t.child = La(t, null, s, a)) : Is(e, t, s, a), t.memoizedState = r.state, i && ta(t, n, !0), t.child;
	}
	function Gs(e) {
		var t = e.stateNode;
		t.pendingContext ? Qi(e, t.pendingContext, t.pendingContext !== t.context) : t.context && Qi(e, t.context, !1), po(e, t.containerInfo);
	}
	function Ks(e, t, n, r, i) {
		return Aa(), ja(i), t.flags |= 256, Is(e, t, n, r), t.child;
	}
	var qs = {
		dehydrated: null,
		treeContext: null,
		retryLane: 0
	};
	function Js(e) {
		return {
			baseLanes: e,
			cachePool: null,
			transitions: null
		};
	}
	function Ys(e, t, n) {
		var r = t.pendingProps, i = J.current, a = !1, o = (t.flags & 128) != 0, s;
		if ((s = o) || (s = e !== null && e.memoizedState === null ? !1 : (i & 2) != 0), s ? (a = !0, t.flags &= -129) : (e === null || e.memoizedState !== null) && (i |= 1), G(J, i & 1), e === null) return Ea(t), e = t.memoizedState, e !== null && (e = e.dehydrated, e !== null) ? (t.mode & 1 ? e.data === "$!" ? t.lanes = 8 : t.lanes = 1073741824 : t.lanes = 1, null) : (o = r.children, e = r.fallback, a ? (r = t.mode, a = t.child, o = {
			mode: "hidden",
			children: o
		}, !(r & 1) && a !== null ? (a.childLanes = 0, a.pendingProps = o) : a = Ql(o, r, 0, null), e = Zl(e, r, n, null), a.return = t, e.return = t, a.sibling = e, t.child = a, t.child.memoizedState = Js(n), t.memoizedState = qs, e) : Xs(t, o));
		if (i = e.memoizedState, i !== null && (s = i.dehydrated, s !== null)) return Qs(e, t, o, r, s, i, n);
		if (a) {
			a = r.fallback, o = t.mode, i = e.child, s = i.sibling;
			var c = {
				mode: "hidden",
				children: r.children
			};
			return !(o & 1) && t.child !== i ? (r = t.child, r.childLanes = 0, r.pendingProps = c, t.deletions = null) : (r = Yl(i, c), r.subtreeFlags = i.subtreeFlags & 14680064), s === null ? (a = Zl(a, o, n, null), a.flags |= 2) : a = Yl(s, a), a.return = t, r.return = t, r.sibling = a, t.child = r, r = a, a = t.child, o = e.child.memoizedState, o = o === null ? Js(n) : {
				baseLanes: o.baseLanes | n,
				cachePool: null,
				transitions: o.transitions
			}, a.memoizedState = o, a.childLanes = e.childLanes & ~n, t.memoizedState = qs, r;
		}
		return a = e.child, e = a.sibling, r = Yl(a, {
			mode: "visible",
			children: r.children
		}), !(t.mode & 1) && (r.lanes = n), r.return = t, r.sibling = null, e !== null && (n = t.deletions, n === null ? (t.deletions = [e], t.flags |= 16) : n.push(e)), t.child = r, t.memoizedState = null, r;
	}
	function Xs(e, t) {
		return t = Ql({
			mode: "visible",
			children: t
		}, e.mode, 0, null), t.return = e, e.child = t;
	}
	function Zs(e, t, n, r) {
		return r !== null && ja(r), La(t, e.child, null, n), e = Xs(t, t.pendingProps.children), e.flags |= 2, t.memoizedState = null, e;
	}
	function Qs(e, t, n, i, a, o, s) {
		if (n) return t.flags & 256 ? (t.flags &= -257, i = Es(Error(r(422))), Zs(e, t, s, i)) : t.memoizedState === null ? (o = i.fallback, a = t.mode, i = Ql({
			mode: "visible",
			children: i.children
		}, a, 0, null), o = Zl(o, a, s, null), o.flags |= 2, i.return = t, o.return = t, i.sibling = o, t.child = i, t.mode & 1 && La(t, e.child, null, s), t.child.memoizedState = Js(s), t.memoizedState = qs, o) : (t.child = e.child, t.flags |= 128, null);
		if (!(t.mode & 1)) return Zs(e, t, s, null);
		if (a.data === "$!") {
			if (i = a.nextSibling && a.nextSibling.dataset, i) var c = i.dgst;
			return i = c, o = Error(r(419)), i = Es(o, i, void 0), Zs(e, t, s, i);
		}
		if (c = (s & e.childLanes) !== 0, Fs || c) {
			if (i = Vc, i !== null) {
				switch (s & -s) {
					case 4:
						a = 2;
						break;
					case 16:
						a = 8;
						break;
					case 64:
					case 128:
					case 256:
					case 512:
					case 1024:
					case 2048:
					case 4096:
					case 8192:
					case 16384:
					case 32768:
					case 65536:
					case 131072:
					case 262144:
					case 524288:
					case 1048576:
					case 2097152:
					case 4194304:
					case 8388608:
					case 16777216:
					case 33554432:
					case 67108864:
						a = 32;
						break;
					case 536870912:
						a = 268435456;
						break;
					default: a = 0;
				}
				a = (a & (i.suspendedLanes | s)) === 0 ? a : 0, a !== 0 && a !== o.retryLane && (o.retryLane = a, Za(e, a), ml(i, e, a, -1));
			}
			return Ol(), i = Es(Error(r(421))), Zs(e, t, s, i);
		}
		return a.data === "$?" ? (t.flags |= 128, t.child = e.child, t = Vl.bind(null, e), a._reactRetry = t, null) : (e = o.treeContext, Sa = ki(a.nextSibling), xa = t, K = !0, Ca = null, e !== null && (fa[pa++] = ha, fa[pa++] = ga, fa[pa++] = ma, ha = e.id, ga = e.overflow, ma = t), t = Xs(t, i.children), t.flags |= 4096, t);
	}
	function $s(e, t, n) {
		e.lanes |= t;
		var r = e.alternate;
		r !== null && (r.lanes |= t), Ga(e.return, t, n);
	}
	function ec(e, t, n, r, i) {
		var a = e.memoizedState;
		a === null ? e.memoizedState = {
			isBackwards: t,
			rendering: null,
			renderingStartTime: 0,
			last: r,
			tail: n,
			tailMode: i
		} : (a.isBackwards = t, a.rendering = null, a.renderingStartTime = 0, a.last = r, a.tail = n, a.tailMode = i);
	}
	function tc(e, t, n) {
		var r = t.pendingProps, i = r.revealOrder, a = r.tail;
		if (Is(e, t, r.children, n), r = J.current, r & 2) r = r & 1 | 2, t.flags |= 128;
		else {
			if (e !== null && e.flags & 128) a: for (e = t.child; e !== null;) {
				if (e.tag === 13) e.memoizedState !== null && $s(e, n, t);
				else if (e.tag === 19) $s(e, n, t);
				else if (e.child !== null) {
					e.child.return = e, e = e.child;
					continue;
				}
				if (e === t) break a;
				for (; e.sibling === null;) {
					if (e.return === null || e.return === t) break a;
					e = e.return;
				}
				e.sibling.return = e.return, e = e.sibling;
			}
			r &= 1;
		}
		if (G(J, r), !(t.mode & 1)) t.memoizedState = null;
		else switch (i) {
			case "forwards":
				for (n = t.child, i = null; n !== null;) e = n.alternate, e !== null && _o(e) === null && (i = n), n = n.sibling;
				n = i, n === null ? (i = t.child, t.child = null) : (i = n.sibling, n.sibling = null), ec(t, !1, i, n, a);
				break;
			case "backwards":
				for (n = null, i = t.child, t.child = null; i !== null;) {
					if (e = i.alternate, e !== null && _o(e) === null) {
						t.child = i;
						break;
					}
					e = i.sibling, i.sibling = n, n = i, i = e;
				}
				ec(t, !0, n, null, a);
				break;
			case "together":
				ec(t, !1, null, null, void 0);
				break;
			default: t.memoizedState = null;
		}
		return t.child;
	}
	function nc(e, t) {
		!(t.mode & 1) && e !== null && (e.alternate = null, t.alternate = null, t.flags |= 2);
	}
	function rc(e, t, n) {
		if (e !== null && (t.dependencies = e.dependencies), Jc |= t.lanes, (n & t.childLanes) === 0) return null;
		if (e !== null && t.child !== e.child) throw Error(r(153));
		if (t.child !== null) {
			for (e = t.child, n = Yl(e, e.pendingProps), t.child = n, n.return = t; e.sibling !== null;) e = e.sibling, n = n.sibling = Yl(e, e.pendingProps), n.return = t;
			n.sibling = null;
		}
		return t.child;
	}
	function ic(e, t, n) {
		switch (t.tag) {
			case 3:
				Gs(t), Aa();
				break;
			case 5:
				ho(t);
				break;
			case 1:
				Xi(t.type) && ea(t);
				break;
			case 4:
				po(t, t.stateNode.containerInfo);
				break;
			case 10:
				var r = t.type._context, i = t.memoizedProps.value;
				G(za, r._currentValue), r._currentValue = i;
				break;
			case 13:
				if (r = t.memoizedState, r !== null) return r.dehydrated === null ? (n & t.child.childLanes) === 0 ? (G(J, J.current & 1), e = rc(e, t, n), e === null ? null : e.sibling) : Ys(e, t, n) : (G(J, J.current & 1), t.flags |= 128, null);
				G(J, J.current & 1);
				break;
			case 19:
				if (r = (n & t.childLanes) !== 0, e.flags & 128) {
					if (r) return tc(e, t, n);
					t.flags |= 128;
				}
				if (i = t.memoizedState, i !== null && (i.rendering = null, i.tail = null, i.lastEffect = null), G(J, J.current), r) break;
				return null;
			case 22:
			case 23: return t.lanes = 0, Bs(e, t, n);
		}
		return rc(e, t, n);
	}
	var ac = function(e, t) {
		for (var n = t.child; n !== null;) {
			if (n.tag === 5 || n.tag === 6) e.appendChild(n.stateNode);
			else if (n.tag !== 4 && n.child !== null) {
				n.child.return = n, n = n.child;
				continue;
			}
			if (n === t) break;
			for (; n.sibling === null;) {
				if (n.return === null || n.return === t) return;
				n = n.return;
			}
			n.sibling.return = n.return, n = n.sibling;
		}
	}, oc = function(e, t, n, r) {
		var i = e.memoizedProps;
		if (i !== r) {
			e = t.stateNode, fo(co.current);
			var o = null;
			switch (n) {
				case "input":
					i = fe(e, i), r = fe(e, r), o = [];
					break;
				case "select":
					i = R({}, i, { value: void 0 }), r = R({}, r, { value: void 0 }), o = [];
					break;
				case "textarea":
					i = be(e, i), r = be(e, r), o = [];
					break;
				default: typeof i.onClick != "function" && typeof r.onClick == "function" && (e.onclick = yi);
			}
			Pe(n, r);
			var s;
			for (u in n = null, i) if (!r.hasOwnProperty(u) && i.hasOwnProperty(u) && i[u] != null) if (u === "style") {
				var c = i[u];
				for (s in c) c.hasOwnProperty(s) && (n ||= {}, n[s] = "");
			} else u !== "dangerouslySetInnerHTML" && u !== "children" && u !== "suppressContentEditableWarning" && u !== "suppressHydrationWarning" && u !== "autoFocus" && (a.hasOwnProperty(u) ? o ||= [] : (o ||= []).push(u, null));
			for (u in r) {
				var l = r[u];
				if (c = i?.[u], r.hasOwnProperty(u) && l !== c && (l != null || c != null)) if (u === "style") if (c) {
					for (s in c) !c.hasOwnProperty(s) || l && l.hasOwnProperty(s) || (n ||= {}, n[s] = "");
					for (s in l) l.hasOwnProperty(s) && c[s] !== l[s] && (n ||= {}, n[s] = l[s]);
				} else n || (o ||= [], o.push(u, n)), n = l;
				else u === "dangerouslySetInnerHTML" ? (l = l ? l.__html : void 0, c = c ? c.__html : void 0, l != null && c !== l && (o ||= []).push(u, l)) : u === "children" ? typeof l != "string" && typeof l != "number" || (o ||= []).push(u, "" + l) : u !== "suppressContentEditableWarning" && u !== "suppressHydrationWarning" && (a.hasOwnProperty(u) ? (l != null && u === "onScroll" && U("scroll", e), o || c === l || (o = [])) : (o ||= []).push(u, l));
			}
			n && (o ||= []).push("style", n);
			var u = o;
			(t.updateQueue = u) && (t.flags |= 4);
		}
	}, sc = function(e, t, n, r) {
		n !== r && (t.flags |= 4);
	};
	function cc(e, t) {
		if (!K) switch (e.tailMode) {
			case "hidden":
				t = e.tail;
				for (var n = null; t !== null;) t.alternate !== null && (n = t), t = t.sibling;
				n === null ? e.tail = null : n.sibling = null;
				break;
			case "collapsed":
				n = e.tail;
				for (var r = null; n !== null;) n.alternate !== null && (r = n), n = n.sibling;
				r === null ? t || e.tail === null ? e.tail = null : e.tail.sibling = null : r.sibling = null;
		}
	}
	function lc(e) {
		var t = e.alternate !== null && e.alternate.child === e.child, n = 0, r = 0;
		if (t) for (var i = e.child; i !== null;) n |= i.lanes | i.childLanes, r |= i.subtreeFlags & 14680064, r |= i.flags & 14680064, i.return = e, i = i.sibling;
		else for (i = e.child; i !== null;) n |= i.lanes | i.childLanes, r |= i.subtreeFlags, r |= i.flags, i.return = e, i = i.sibling;
		return e.subtreeFlags |= r, e.childLanes = n, t;
	}
	function uc(e, t, n) {
		var i = t.pendingProps;
		switch (ba(t), t.tag) {
			case 2:
			case 16:
			case 15:
			case 0:
			case 11:
			case 7:
			case 8:
			case 12:
			case 9:
			case 14: return lc(t), null;
			case 1: return Xi(t.type) && Zi(), lc(t), null;
			case 3: return i = t.stateNode, mo(), W(qi), W(Ki), yo(), i.pendingContext && (i.context = i.pendingContext, i.pendingContext = null), (e === null || e.child === null) && (Oa(t) ? t.flags |= 4 : e === null || e.memoizedState.isDehydrated && !(t.flags & 256) || (t.flags |= 1024, Ca !== null && (vl(Ca), Ca = null))), lc(t), null;
			case 5:
				go(t);
				var o = fo(uo.current);
				if (n = t.type, e !== null && t.stateNode != null) oc(e, t, n, i, o), e.ref !== t.ref && (t.flags |= 512, t.flags |= 2097152);
				else {
					if (!i) {
						if (t.stateNode === null) throw Error(r(166));
						return lc(t), null;
					}
					if (e = fo(co.current), Oa(t)) {
						i = t.stateNode, n = t.type;
						var s = t.memoizedProps;
						switch (i[Mi] = t, i[Ni] = s, e = (t.mode & 1) != 0, n) {
							case "dialog":
								U("cancel", i), U("close", i);
								break;
							case "iframe":
							case "object":
							case "embed":
								U("load", i);
								break;
							case "video":
							case "audio":
								for (o = 0; o < ni.length; o++) U(ni[o], i);
								break;
							case "source":
								U("error", i);
								break;
							case "img":
							case "image":
							case "link":
								U("error", i), U("load", i);
								break;
							case "details":
								U("toggle", i);
								break;
							case "input":
								pe(i, s), U("invalid", i);
								break;
							case "select":
								i._wrapperState = { wasMultiple: !!s.multiple }, U("invalid", i);
								break;
							case "textarea": xe(i, s), U("invalid", i);
						}
						for (var c in Pe(n, s), o = null, s) if (s.hasOwnProperty(c)) {
							var l = s[c];
							c === "children" ? typeof l == "string" ? i.textContent !== l && (!0 !== s.suppressHydrationWarning && vi(i.textContent, l, e), o = ["children", l]) : typeof l == "number" && i.textContent !== "" + l && (!0 !== s.suppressHydrationWarning && vi(i.textContent, l, e), o = ["children", "" + l]) : a.hasOwnProperty(c) && l != null && c === "onScroll" && U("scroll", i);
						}
						switch (n) {
							case "input":
								le(i), ge(i, s, !0);
								break;
							case "textarea":
								le(i), Ce(i);
								break;
							case "select":
							case "option": break;
							default: typeof s.onClick == "function" && (i.onclick = yi);
						}
						i = o, t.updateQueue = i, i !== null && (t.flags |= 4);
					} else {
						c = o.nodeType === 9 ? o : o.ownerDocument, e === "http://www.w3.org/1999/xhtml" && (e = we(n)), e === "http://www.w3.org/1999/xhtml" ? n === "script" ? (e = c.createElement("div"), e.innerHTML = "<script><\/script>", e = e.removeChild(e.firstChild)) : typeof i.is == "string" ? e = c.createElement(n, { is: i.is }) : (e = c.createElement(n), n === "select" && (c = e, i.multiple ? c.multiple = !0 : i.size && (c.size = i.size))) : e = c.createElementNS(e, n), e[Mi] = t, e[Ni] = i, ac(e, t, !1, !1), t.stateNode = e;
						a: {
							switch (c = Fe(n, i), n) {
								case "dialog":
									U("cancel", e), U("close", e), o = i;
									break;
								case "iframe":
								case "object":
								case "embed":
									U("load", e), o = i;
									break;
								case "video":
								case "audio":
									for (o = 0; o < ni.length; o++) U(ni[o], e);
									o = i;
									break;
								case "source":
									U("error", e), o = i;
									break;
								case "img":
								case "image":
								case "link":
									U("error", e), U("load", e), o = i;
									break;
								case "details":
									U("toggle", e), o = i;
									break;
								case "input":
									pe(e, i), o = fe(e, i), U("invalid", e);
									break;
								case "option":
									o = i;
									break;
								case "select":
									e._wrapperState = { wasMultiple: !!i.multiple }, o = R({}, i, { value: void 0 }), U("invalid", e);
									break;
								case "textarea":
									xe(e, i), o = be(e, i), U("invalid", e);
									break;
								default: o = i;
							}
							for (s in Pe(n, o), l = o, l) if (l.hasOwnProperty(s)) {
								var u = l[s];
								s === "style" ? Me(e, u) : s === "dangerouslySetInnerHTML" ? (u = u ? u.__html : void 0, u != null && De(e, u)) : s === "children" ? typeof u == "string" ? (n !== "textarea" || u !== "") && Oe(e, u) : typeof u == "number" && Oe(e, "" + u) : s !== "suppressContentEditableWarning" && s !== "suppressHydrationWarning" && s !== "autoFocus" && (a.hasOwnProperty(s) ? u != null && s === "onScroll" && U("scroll", e) : u != null && S(e, s, u, c));
							}
							switch (n) {
								case "input":
									le(e), ge(e, i, !1);
									break;
								case "textarea":
									le(e), Ce(e);
									break;
								case "option":
									i.value != null && e.setAttribute("value", "" + oe(i.value));
									break;
								case "select":
									e.multiple = !!i.multiple, s = i.value, s == null ? i.defaultValue != null && ye(e, !!i.multiple, i.defaultValue, !0) : ye(e, !!i.multiple, s, !1);
									break;
								default: typeof o.onClick == "function" && (e.onclick = yi);
							}
							switch (n) {
								case "button":
								case "input":
								case "select":
								case "textarea":
									i = !!i.autoFocus;
									break a;
								case "img":
									i = !0;
									break a;
								default: i = !1;
							}
						}
						i && (t.flags |= 4);
					}
					t.ref !== null && (t.flags |= 512, t.flags |= 2097152);
				}
				return lc(t), null;
			case 6:
				if (e && t.stateNode != null) sc(e, t, e.memoizedProps, i);
				else {
					if (typeof i != "string" && t.stateNode === null) throw Error(r(166));
					if (n = fo(uo.current), fo(co.current), Oa(t)) {
						if (i = t.stateNode, n = t.memoizedProps, i[Mi] = t, (s = i.nodeValue !== n) && (e = xa, e !== null)) switch (e.tag) {
							case 3:
								vi(i.nodeValue, n, (e.mode & 1) != 0);
								break;
							case 5: !0 !== e.memoizedProps.suppressHydrationWarning && vi(i.nodeValue, n, (e.mode & 1) != 0);
						}
						s && (t.flags |= 4);
					} else i = (n.nodeType === 9 ? n : n.ownerDocument).createTextNode(i), i[Mi] = t, t.stateNode = i;
				}
				return lc(t), null;
			case 13:
				if (W(J), i = t.memoizedState, e === null || e.memoizedState !== null && e.memoizedState.dehydrated !== null) {
					if (K && Sa !== null && t.mode & 1 && !(t.flags & 128)) ka(), Aa(), t.flags |= 98560, s = !1;
					else if (s = Oa(t), i !== null && i.dehydrated !== null) {
						if (e === null) {
							if (!s) throw Error(r(318));
							if (s = t.memoizedState, s = s === null ? null : s.dehydrated, !s) throw Error(r(317));
							s[Mi] = t;
						} else Aa(), !(t.flags & 128) && (t.memoizedState = null), t.flags |= 4;
						lc(t), s = !1;
					} else Ca !== null && (vl(Ca), Ca = null), s = !0;
					if (!s) return t.flags & 65536 ? t : null;
				}
				return t.flags & 128 ? (t.lanes = n, t) : (i = i !== null, i !== (e !== null && e.memoizedState !== null) && i && (t.child.flags |= 8192, t.mode & 1 && (e === null || J.current & 1 ? Kc === 0 && (Kc = 3) : Ol())), t.updateQueue !== null && (t.flags |= 4), lc(t), null);
			case 4: return mo(), e === null && ci(t.stateNode.containerInfo), lc(t), null;
			case 10: return Wa(t.type._context), lc(t), null;
			case 17: return Xi(t.type) && Zi(), lc(t), null;
			case 19:
				if (W(J), s = t.memoizedState, s === null) return lc(t), null;
				if (i = (t.flags & 128) != 0, c = s.rendering, c === null) if (i) cc(s, !1);
				else {
					if (Kc !== 0 || e !== null && e.flags & 128) for (e = t.child; e !== null;) {
						if (c = _o(e), c !== null) {
							for (t.flags |= 128, cc(s, !1), i = c.updateQueue, i !== null && (t.updateQueue = i, t.flags |= 4), t.subtreeFlags = 0, i = n, n = t.child; n !== null;) s = n, e = i, s.flags &= 14680066, c = s.alternate, c === null ? (s.childLanes = 0, s.lanes = e, s.child = null, s.subtreeFlags = 0, s.memoizedProps = null, s.memoizedState = null, s.updateQueue = null, s.dependencies = null, s.stateNode = null) : (s.childLanes = c.childLanes, s.lanes = c.lanes, s.child = c.child, s.subtreeFlags = 0, s.deletions = null, s.memoizedProps = c.memoizedProps, s.memoizedState = c.memoizedState, s.updateQueue = c.updateQueue, s.type = c.type, e = c.dependencies, s.dependencies = e === null ? null : {
								lanes: e.lanes,
								firstContext: e.firstContext
							}), n = n.sibling;
							return G(J, J.current & 1 | 2), t.child;
						}
						e = e.sibling;
					}
					s.tail !== null && ht() > el && (t.flags |= 128, i = !0, cc(s, !1), t.lanes = 4194304);
				}
				else {
					if (!i) if (e = _o(c), e !== null) {
						if (t.flags |= 128, i = !0, n = e.updateQueue, n !== null && (t.updateQueue = n, t.flags |= 4), cc(s, !0), s.tail === null && s.tailMode === "hidden" && !c.alternate && !K) return lc(t), null;
					} else 2 * ht() - s.renderingStartTime > el && n !== 1073741824 && (t.flags |= 128, i = !0, cc(s, !1), t.lanes = 4194304);
					s.isBackwards ? (c.sibling = t.child, t.child = c) : (n = s.last, n === null ? t.child = c : n.sibling = c, s.last = c);
				}
				return s.tail === null ? (lc(t), null) : (t = s.tail, s.rendering = t, s.tail = t.sibling, s.renderingStartTime = ht(), t.sibling = null, n = J.current, G(J, i ? n & 1 | 2 : n & 1), t);
			case 22:
			case 23: return wl(), i = t.memoizedState !== null, e !== null && e.memoizedState !== null !== i && (t.flags |= 8192), i && t.mode & 1 ? Wc & 1073741824 && (lc(t), t.subtreeFlags & 6 && (t.flags |= 8192)) : lc(t), null;
			case 24: return null;
			case 25: return null;
		}
		throw Error(r(156, t.tag));
	}
	function dc(e, t) {
		switch (ba(t), t.tag) {
			case 1: return Xi(t.type) && Zi(), e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 3: return mo(), W(qi), W(Ki), yo(), e = t.flags, e & 65536 && !(e & 128) ? (t.flags = e & -65537 | 128, t) : null;
			case 5: return go(t), null;
			case 13:
				if (W(J), e = t.memoizedState, e !== null && e.dehydrated !== null) {
					if (t.alternate === null) throw Error(r(340));
					Aa();
				}
				return e = t.flags, e & 65536 ? (t.flags = e & -65537 | 128, t) : null;
			case 19: return W(J), null;
			case 4: return mo(), null;
			case 10: return Wa(t.type._context), null;
			case 22:
			case 23: return wl(), null;
			case 24: return null;
			default: return null;
		}
	}
	var Y = !1, fc = !1, pc = typeof WeakSet == "function" ? WeakSet : Set, X = null;
	function Z(e, t) {
		var n = e.ref;
		if (n !== null) if (typeof n == "function") try {
			n(null);
		} catch (n) {
			Rl(e, t, n);
		}
		else n.current = null;
	}
	function Q(e, t, n) {
		try {
			n();
		} catch (n) {
			Rl(e, t, n);
		}
	}
	var mc = !1;
	function hc(e, t) {
		if (bi = pn, e = Nr(), Pr(e)) {
			if ("selectionStart" in e) var n = {
				start: e.selectionStart,
				end: e.selectionEnd
			};
			else a: {
				n = (n = e.ownerDocument) && n.defaultView || window;
				var i = n.getSelection && n.getSelection();
				if (i && i.rangeCount !== 0) {
					n = i.anchorNode;
					var a = i.anchorOffset, o = i.focusNode;
					i = i.focusOffset;
					try {
						n.nodeType, o.nodeType;
					} catch {
						n = null;
						break a;
					}
					var s = 0, c = -1, l = -1, u = 0, d = 0, f = e, p = null;
					b: for (;;) {
						for (var m; f !== n || a !== 0 && f.nodeType !== 3 || (c = s + a), f !== o || i !== 0 && f.nodeType !== 3 || (l = s + i), f.nodeType === 3 && (s += f.nodeValue.length), (m = f.firstChild) !== null;) p = f, f = m;
						for (;;) {
							if (f === e) break b;
							if (p === n && ++u === a && (c = s), p === o && ++d === i && (l = s), (m = f.nextSibling) !== null) break;
							f = p, p = f.parentNode;
						}
						f = m;
					}
					n = c === -1 || l === -1 ? null : {
						start: c,
						end: l
					};
				} else n = null;
			}
			n ||= {
				start: 0,
				end: 0
			};
		} else n = null;
		for (xi = {
			focusedElem: e,
			selectionRange: n
		}, pn = !1, X = t; X !== null;) if (t = X, e = t.child, t.subtreeFlags & 1028 && e !== null) e.return = t, X = e;
		else for (; X !== null;) {
			t = X;
			try {
				var h = t.alternate;
				if (t.flags & 1024) switch (t.tag) {
					case 0:
					case 11:
					case 15: break;
					case 1:
						if (h !== null) {
							var g = h.memoizedProps, _ = h.memoizedState, v = t.stateNode;
							v.__reactInternalSnapshotBeforeUpdate = v.getSnapshotBeforeUpdate(t.elementType === t.type ? g : vs(t.type, g), _);
						}
						break;
					case 3:
						var y = t.stateNode.containerInfo;
						y.nodeType === 1 ? y.textContent = "" : y.nodeType === 9 && y.documentElement && y.removeChild(y.documentElement);
						break;
					case 5:
					case 6:
					case 4:
					case 17: break;
					default: throw Error(r(163));
				}
			} catch (e) {
				Rl(t, t.return, e);
			}
			if (e = t.sibling, e !== null) {
				e.return = t.return, X = e;
				break;
			}
			X = t.return;
		}
		return h = mc, mc = !1, h;
	}
	function gc(e, t, n) {
		var r = t.updateQueue;
		if (r = r === null ? null : r.lastEffect, r !== null) {
			var i = r = r.next;
			do {
				if ((i.tag & e) === e) {
					var a = i.destroy;
					i.destroy = void 0, a !== void 0 && Q(t, n, a);
				}
				i = i.next;
			} while (i !== r);
		}
	}
	function _c(e, t) {
		if (t = t.updateQueue, t = t === null ? null : t.lastEffect, t !== null) {
			var n = t = t.next;
			do {
				if ((n.tag & e) === e) {
					var r = n.create;
					n.destroy = r();
				}
				n = n.next;
			} while (n !== t);
		}
	}
	function vc(e) {
		var t = e.ref;
		if (t !== null) {
			var n = e.stateNode;
			switch (e.tag) {
				case 5:
					e = n;
					break;
				default: e = n;
			}
			typeof t == "function" ? t(e) : t.current = e;
		}
	}
	function yc(e) {
		var t = e.alternate;
		t !== null && (e.alternate = null, yc(t)), e.child = null, e.deletions = null, e.sibling = null, e.tag === 5 && (t = e.stateNode, t !== null && (delete t[Mi], delete t[Ni], delete t[Fi], delete t[Ii], delete t[Li])), e.stateNode = null, e.return = null, e.dependencies = null, e.memoizedProps = null, e.memoizedState = null, e.pendingProps = null, e.stateNode = null, e.updateQueue = null;
	}
	function bc(e) {
		return e.tag === 5 || e.tag === 3 || e.tag === 4;
	}
	function xc(e) {
		a: for (;;) {
			for (; e.sibling === null;) {
				if (e.return === null || bc(e.return)) return null;
				e = e.return;
			}
			for (e.sibling.return = e.return, e = e.sibling; e.tag !== 5 && e.tag !== 6 && e.tag !== 18;) {
				if (e.flags & 2 || e.child === null || e.tag === 4) continue a;
				e.child.return = e, e = e.child;
			}
			if (!(e.flags & 2)) return e.stateNode;
		}
	}
	function Sc(e, t, n) {
		var r = e.tag;
		if (r === 5 || r === 6) e = e.stateNode, t ? n.nodeType === 8 ? n.parentNode.insertBefore(e, t) : n.insertBefore(e, t) : (n.nodeType === 8 ? (t = n.parentNode, t.insertBefore(e, n)) : (t = n, t.appendChild(e)), n = n._reactRootContainer, n != null || t.onclick !== null || (t.onclick = yi));
		else if (r !== 4 && (e = e.child, e !== null)) for (Sc(e, t, n), e = e.sibling; e !== null;) Sc(e, t, n), e = e.sibling;
	}
	function Cc(e, t, n) {
		var r = e.tag;
		if (r === 5 || r === 6) e = e.stateNode, t ? n.insertBefore(e, t) : n.appendChild(e);
		else if (r !== 4 && (e = e.child, e !== null)) for (Cc(e, t, n), e = e.sibling; e !== null;) Cc(e, t, n), e = e.sibling;
	}
	var wc = null, Tc = !1;
	function Ec(e, t, n) {
		for (n = n.child; n !== null;) Dc(e, t, n), n = n.sibling;
	}
	function Dc(e, t, n) {
		if (Ct && typeof Ct.onCommitFiberUnmount == "function") try {
			Ct.onCommitFiberUnmount(St, n);
		} catch {}
		switch (n.tag) {
			case 5: fc || Z(n, t);
			case 6:
				var r = wc, i = Tc;
				wc = null, Ec(e, t, n), wc = r, Tc = i, wc !== null && (Tc ? (e = wc, n = n.stateNode, e.nodeType === 8 ? e.parentNode.removeChild(n) : e.removeChild(n)) : wc.removeChild(n.stateNode));
				break;
			case 18:
				wc !== null && (Tc ? (e = wc, n = n.stateNode, e.nodeType === 8 ? Oi(e.parentNode, n) : e.nodeType === 1 && Oi(e, n), dn(e)) : Oi(wc, n.stateNode));
				break;
			case 4:
				r = wc, i = Tc, wc = n.stateNode.containerInfo, Tc = !0, Ec(e, t, n), wc = r, Tc = i;
				break;
			case 0:
			case 11:
			case 14:
			case 15:
				if (!fc && (r = n.updateQueue, r !== null && (r = r.lastEffect, r !== null))) {
					i = r = r.next;
					do {
						var a = i, o = a.destroy;
						a = a.tag, o !== void 0 && (a & 2 || a & 4) && Q(n, t, o), i = i.next;
					} while (i !== r);
				}
				Ec(e, t, n);
				break;
			case 1:
				if (!fc && (Z(n, t), r = n.stateNode, typeof r.componentWillUnmount == "function")) try {
					r.props = n.memoizedProps, r.state = n.memoizedState, r.componentWillUnmount();
				} catch (e) {
					Rl(n, t, e);
				}
				Ec(e, t, n);
				break;
			case 21:
				Ec(e, t, n);
				break;
			case 22:
				n.mode & 1 ? (fc = (r = fc) || n.memoizedState !== null, Ec(e, t, n), fc = r) : Ec(e, t, n);
				break;
			default: Ec(e, t, n);
		}
	}
	function Oc(e) {
		var t = e.updateQueue;
		if (t !== null) {
			e.updateQueue = null;
			var n = e.stateNode;
			n === null && (n = e.stateNode = new pc()), t.forEach(function(t) {
				var r = Hl.bind(null, e, t);
				n.has(t) || (n.add(t), t.then(r, r));
			});
		}
	}
	function kc(e, t) {
		var n = t.deletions;
		if (n !== null) for (var i = 0; i < n.length; i++) {
			var a = n[i];
			try {
				var o = e, s = t, c = s;
				a: for (; c !== null;) {
					switch (c.tag) {
						case 5:
							wc = c.stateNode, Tc = !1;
							break a;
						case 3:
							wc = c.stateNode.containerInfo, Tc = !0;
							break a;
						case 4:
							wc = c.stateNode.containerInfo, Tc = !0;
							break a;
					}
					c = c.return;
				}
				if (wc === null) throw Error(r(160));
				Dc(o, s, a), wc = null, Tc = !1;
				var l = a.alternate;
				l !== null && (l.return = null), a.return = null;
			} catch (e) {
				Rl(a, t, e);
			}
		}
		if (t.subtreeFlags & 12854) for (t = t.child; t !== null;) Ac(t, e), t = t.sibling;
	}
	function Ac(e, t) {
		var n = e.alternate, i = e.flags;
		switch (e.tag) {
			case 0:
			case 11:
			case 14:
			case 15:
				if (kc(t, e), jc(e), i & 4) {
					try {
						gc(3, e, e.return), _c(3, e);
					} catch (t) {
						Rl(e, e.return, t);
					}
					try {
						gc(5, e, e.return);
					} catch (t) {
						Rl(e, e.return, t);
					}
				}
				break;
			case 1:
				kc(t, e), jc(e), i & 512 && n !== null && Z(n, n.return);
				break;
			case 5:
				if (kc(t, e), jc(e), i & 512 && n !== null && Z(n, n.return), e.flags & 32) {
					var a = e.stateNode;
					try {
						Oe(a, "");
					} catch (t) {
						Rl(e, e.return, t);
					}
				}
				if (i & 4 && (a = e.stateNode, a != null)) {
					var o = e.memoizedProps, s = n === null ? o : n.memoizedProps, c = e.type, l = e.updateQueue;
					if (e.updateQueue = null, l !== null) try {
						c === "input" && o.type === "radio" && o.name != null && me(a, o), Fe(c, s);
						var u = Fe(c, o);
						for (s = 0; s < l.length; s += 2) {
							var d = l[s], f = l[s + 1];
							d === "style" ? Me(a, f) : d === "dangerouslySetInnerHTML" ? De(a, f) : d === "children" ? Oe(a, f) : S(a, d, f, u);
						}
						switch (c) {
							case "input":
								he(a, o);
								break;
							case "textarea":
								Se(a, o);
								break;
							case "select":
								var p = a._wrapperState.wasMultiple;
								a._wrapperState.wasMultiple = !!o.multiple;
								var m = o.value;
								m == null ? p !== !!o.multiple && (o.defaultValue == null ? ye(a, !!o.multiple, o.multiple ? [] : "", !1) : ye(a, !!o.multiple, o.defaultValue, !0)) : ye(a, !!o.multiple, m, !1);
						}
						a[Ni] = o;
					} catch (t) {
						Rl(e, e.return, t);
					}
				}
				break;
			case 6:
				if (kc(t, e), jc(e), i & 4) {
					if (e.stateNode === null) throw Error(r(162));
					a = e.stateNode, o = e.memoizedProps;
					try {
						a.nodeValue = o;
					} catch (t) {
						Rl(e, e.return, t);
					}
				}
				break;
			case 3:
				if (kc(t, e), jc(e), i & 4 && n !== null && n.memoizedState.isDehydrated) try {
					dn(t.containerInfo);
				} catch (t) {
					Rl(e, e.return, t);
				}
				break;
			case 4:
				kc(t, e), jc(e);
				break;
			case 13:
				kc(t, e), jc(e), a = e.child, a.flags & 8192 && (o = a.memoizedState !== null, a.stateNode.isHidden = o, !o || a.alternate !== null && a.alternate.memoizedState !== null || ($c = ht())), i & 4 && Oc(e);
				break;
			case 22:
				if (d = n !== null && n.memoizedState !== null, e.mode & 1 ? (fc = (u = fc) || d, kc(t, e), fc = u) : kc(t, e), jc(e), i & 8192) {
					if (u = e.memoizedState !== null, (e.stateNode.isHidden = u) && !d && e.mode & 1) for (X = e, d = e.child; d !== null;) {
						for (f = X = d; X !== null;) {
							switch (p = X, m = p.child, p.tag) {
								case 0:
								case 11:
								case 14:
								case 15:
									gc(4, p, p.return);
									break;
								case 1:
									Z(p, p.return);
									var h = p.stateNode;
									if (typeof h.componentWillUnmount == "function") {
										i = p, n = p.return;
										try {
											t = i, h.props = t.memoizedProps, h.state = t.memoizedState, h.componentWillUnmount();
										} catch (e) {
											Rl(i, n, e);
										}
									}
									break;
								case 5:
									Z(p, p.return);
									break;
								case 22: if (p.memoizedState !== null) {
									Fc(f);
									continue;
								}
							}
							m === null ? Fc(f) : (m.return = p, X = m);
						}
						d = d.sibling;
					}
					a: for (d = null, f = e;;) {
						if (f.tag === 5) {
							if (d === null) {
								d = f;
								try {
									a = f.stateNode, u ? (o = a.style, typeof o.setProperty == "function" ? o.setProperty("display", "none", "important") : o.display = "none") : (c = f.stateNode, l = f.memoizedProps.style, s = l != null && l.hasOwnProperty("display") ? l.display : null, c.style.display = je("display", s));
								} catch (t) {
									Rl(e, e.return, t);
								}
							}
						} else if (f.tag === 6) {
							if (d === null) try {
								f.stateNode.nodeValue = u ? "" : f.memoizedProps;
							} catch (t) {
								Rl(e, e.return, t);
							}
						} else if ((f.tag !== 22 && f.tag !== 23 || f.memoizedState === null || f === e) && f.child !== null) {
							f.child.return = f, f = f.child;
							continue;
						}
						if (f === e) break a;
						for (; f.sibling === null;) {
							if (f.return === null || f.return === e) break a;
							d === f && (d = null), f = f.return;
						}
						d === f && (d = null), f.sibling.return = f.return, f = f.sibling;
					}
				}
				break;
			case 19:
				kc(t, e), jc(e), i & 4 && Oc(e);
				break;
			case 21: break;
			default: kc(t, e), jc(e);
		}
	}
	function jc(e) {
		var t = e.flags;
		if (t & 2) {
			try {
				a: {
					for (var n = e.return; n !== null;) {
						if (bc(n)) {
							var i = n;
							break a;
						}
						n = n.return;
					}
					throw Error(r(160));
				}
				switch (i.tag) {
					case 5:
						var a = i.stateNode;
						i.flags & 32 && (Oe(a, ""), i.flags &= -33), Cc(e, xc(e), a);
						break;
					case 3:
					case 4:
						var o = i.stateNode.containerInfo;
						Sc(e, xc(e), o);
						break;
					default: throw Error(r(161));
				}
			} catch (t) {
				Rl(e, e.return, t);
			}
			e.flags &= -3;
		}
		t & 4096 && (e.flags &= -4097);
	}
	function Mc(e, t, n) {
		X = e, Nc(e, t, n);
	}
	function Nc(e, t, n) {
		for (var r = (e.mode & 1) != 0; X !== null;) {
			var i = X, a = i.child;
			if (i.tag === 22 && r) {
				var o = i.memoizedState !== null || Y;
				if (!o) {
					var s = i.alternate, c = s !== null && s.memoizedState !== null || fc;
					s = Y;
					var l = fc;
					if (Y = o, (fc = c) && !l) for (X = i; X !== null;) o = X, c = o.child, o.tag === 22 && o.memoizedState !== null || c === null ? Ic(i) : (c.return = o, X = c);
					for (; a !== null;) X = a, Nc(a, t, n), a = a.sibling;
					X = i, Y = s, fc = l;
				}
				Pc(e, t, n);
			} else i.subtreeFlags & 8772 && a !== null ? (a.return = i, X = a) : Pc(e, t, n);
		}
	}
	function Pc(e) {
		for (; X !== null;) {
			var t = X;
			if (t.flags & 8772) {
				var n = t.alternate;
				try {
					if (t.flags & 8772) switch (t.tag) {
						case 0:
						case 11:
						case 15:
							fc || _c(5, t);
							break;
						case 1:
							var i = t.stateNode;
							if (t.flags & 4 && !fc) if (n === null) i.componentDidMount();
							else {
								var a = t.elementType === t.type ? n.memoizedProps : vs(t.type, n.memoizedProps);
								i.componentDidUpdate(a, n.memoizedState, i.__reactInternalSnapshotBeforeUpdate);
							}
							var o = t.updateQueue;
							o !== null && oo(t, o, i);
							break;
						case 3:
							var s = t.updateQueue;
							if (s !== null) {
								if (n = null, t.child !== null) switch (t.child.tag) {
									case 5:
										n = t.child.stateNode;
										break;
									case 1: n = t.child.stateNode;
								}
								oo(t, s, n);
							}
							break;
						case 5:
							var c = t.stateNode;
							if (n === null && t.flags & 4) {
								n = c;
								var l = t.memoizedProps;
								switch (t.type) {
									case "button":
									case "input":
									case "select":
									case "textarea":
										l.autoFocus && n.focus();
										break;
									case "img": l.src && (n.src = l.src);
								}
							}
							break;
						case 6: break;
						case 4: break;
						case 12: break;
						case 13:
							if (t.memoizedState === null) {
								var u = t.alternate;
								if (u !== null) {
									var d = u.memoizedState;
									if (d !== null) {
										var f = d.dehydrated;
										f !== null && dn(f);
									}
								}
							}
							break;
						case 19:
						case 17:
						case 21:
						case 22:
						case 23:
						case 25: break;
						default: throw Error(r(163));
					}
					fc || t.flags & 512 && vc(t);
				} catch (e) {
					Rl(t, t.return, e);
				}
			}
			if (t === e) {
				X = null;
				break;
			}
			if (n = t.sibling, n !== null) {
				n.return = t.return, X = n;
				break;
			}
			X = t.return;
		}
	}
	function Fc(e) {
		for (; X !== null;) {
			var t = X;
			if (t === e) {
				X = null;
				break;
			}
			var n = t.sibling;
			if (n !== null) {
				n.return = t.return, X = n;
				break;
			}
			X = t.return;
		}
	}
	function Ic(e) {
		for (; X !== null;) {
			var t = X;
			try {
				switch (t.tag) {
					case 0:
					case 11:
					case 15:
						var n = t.return;
						try {
							_c(4, t);
						} catch (e) {
							Rl(t, n, e);
						}
						break;
					case 1:
						var r = t.stateNode;
						if (typeof r.componentDidMount == "function") {
							var i = t.return;
							try {
								r.componentDidMount();
							} catch (e) {
								Rl(t, i, e);
							}
						}
						var a = t.return;
						try {
							vc(t);
						} catch (e) {
							Rl(t, a, e);
						}
						break;
					case 5:
						var o = t.return;
						try {
							vc(t);
						} catch (e) {
							Rl(t, o, e);
						}
				}
			} catch (e) {
				Rl(t, t.return, e);
			}
			if (t === e) {
				X = null;
				break;
			}
			var s = t.sibling;
			if (s !== null) {
				s.return = t.return, X = s;
				break;
			}
			X = t.return;
		}
	}
	var Lc = Math.ceil, Rc = C.ReactCurrentDispatcher, zc = C.ReactCurrentOwner, Bc = C.ReactCurrentBatchConfig, $ = 0, Vc = null, Hc = null, Uc = 0, Wc = 0, Gc = Wi(0), Kc = 0, qc = null, Jc = 0, Yc = 0, Xc = 0, Zc = null, Qc = null, $c = 0, el = Infinity, tl = null, nl = !1, rl = null, il = null, al = !1, ol = null, sl = 0, cl = 0, ll = null, ul = -1, dl = 0;
	function fl() {
		return $ & 6 ? ht() : ul === -1 ? ul = ht() : ul;
	}
	function pl(e) {
		return e.mode & 1 ? $ & 2 && Uc !== 0 ? Uc & -Uc : Ma.transition === null ? (e = V, e === 0 ? (e = window.event, e = e === void 0 ? 16 : yn(e.type), e) : e) : (dl === 0 && (dl = It()), dl) : 1;
	}
	function ml(e, t, n, i) {
		if (50 < cl) throw cl = 0, ll = null, Error(r(185));
		Rt(e, n, i), (!($ & 2) || e !== Vc) && (e === Vc && (!($ & 2) && (Yc |= n), Kc === 4 && bl(e, Uc)), hl(e, i), n === 1 && $ === 0 && !(t.mode & 1) && (el = ht() + 500, ra && sa()));
	}
	function hl(e, t) {
		var n = e.callbackNode;
		Pt(e, t);
		var r = Mt(e, e === Vc ? Uc : 0);
		if (r === 0) n !== null && ft(n), e.callbackNode = null, e.callbackPriority = 0;
		else if (t = r & -r, e.callbackPriority !== t) {
			if (n != null && ft(n), t === 1) e.tag === 0 ? oa(xl.bind(null, e)) : aa(xl.bind(null, e)), Ei(function() {
				!($ & 6) && sa();
			}), n = null;
			else {
				switch (Vt(r)) {
					case 1:
						n = _t;
						break;
					case 4:
						n = vt;
						break;
					case 16:
						n = yt;
						break;
					case 536870912:
						n = xt;
						break;
					default: n = yt;
				}
				n = Wl(n, gl.bind(null, e));
			}
			e.callbackPriority = t, e.callbackNode = n;
		}
	}
	function gl(e, t) {
		if (ul = -1, dl = 0, $ & 6) throw Error(r(327));
		var n = e.callbackNode;
		if (Il() && e.callbackNode !== n) return null;
		var i = Mt(e, e === Vc ? Uc : 0);
		if (i === 0) return null;
		if (i & 30 || (i & e.expiredLanes) !== 0 || t) t = kl(e, i);
		else {
			t = i;
			var a = $;
			$ |= 2;
			var o = Dl();
			(Vc !== e || Uc !== t) && (tl = null, el = ht() + 500, Tl(e, t));
			do
				try {
					jl();
					break;
				} catch (t) {
					El(e, t);
				}
			while (1);
			Ua(), Rc.current = o, $ = a, Hc === null ? (Vc = null, Uc = 0, t = Kc) : t = 0;
		}
		if (t !== 0) {
			if (t === 2 && (a = Ft(e), a !== 0 && (i = a, t = _l(e, a))), t === 1) throw n = qc, Tl(e, 0), bl(e, i), hl(e, ht()), n;
			if (t === 6) bl(e, i);
			else {
				if (a = e.current.alternate, !(i & 30) && !yl(a) && (t = kl(e, i), t === 2 && (o = Ft(e), o !== 0 && (i = o, t = _l(e, o))), t === 1)) throw n = qc, Tl(e, 0), bl(e, i), hl(e, ht()), n;
				switch (e.finishedWork = a, e.finishedLanes = i, t) {
					case 0:
					case 1: throw Error(r(345));
					case 2:
						Pl(e, Qc, tl);
						break;
					case 3:
						if (bl(e, i), (i & 130023424) === i && (t = $c + 500 - ht(), 10 < t)) {
							if (Mt(e, 0) !== 0) break;
							if (a = e.suspendedLanes, (a & i) !== i) {
								fl(), e.pingedLanes |= e.suspendedLanes & a;
								break;
							}
							e.timeoutHandle = Ci(Pl.bind(null, e, Qc, tl), t);
							break;
						}
						Pl(e, Qc, tl);
						break;
					case 4:
						if (bl(e, i), (i & 4194240) === i) break;
						for (t = e.eventTimes, a = -1; 0 < i;) {
							var s = 31 - Tt(i);
							o = 1 << s, s = t[s], s > a && (a = s), i &= ~o;
						}
						if (i = a, i = ht() - i, i = (120 > i ? 120 : 480 > i ? 480 : 1080 > i ? 1080 : 1920 > i ? 1920 : 3e3 > i ? 3e3 : 4320 > i ? 4320 : 1960 * Lc(i / 1960)) - i, 10 < i) {
							e.timeoutHandle = Ci(Pl.bind(null, e, Qc, tl), i);
							break;
						}
						Pl(e, Qc, tl);
						break;
					case 5:
						Pl(e, Qc, tl);
						break;
					default: throw Error(r(329));
				}
			}
		}
		return hl(e, ht()), e.callbackNode === n ? gl.bind(null, e) : null;
	}
	function _l(e, t) {
		var n = Zc;
		return e.current.memoizedState.isDehydrated && (Tl(e, t).flags |= 256), e = kl(e, t), e !== 2 && (t = Qc, Qc = n, t !== null && vl(t)), e;
	}
	function vl(e) {
		Qc === null ? Qc = e : Qc.push.apply(Qc, e);
	}
	function yl(e) {
		for (var t = e;;) {
			if (t.flags & 16384) {
				var n = t.updateQueue;
				if (n !== null && (n = n.stores, n !== null)) for (var r = 0; r < n.length; r++) {
					var i = n[r], a = i.getSnapshot;
					i = i.value;
					try {
						if (!Or(a(), i)) return !1;
					} catch {
						return !1;
					}
				}
			}
			if (n = t.child, t.subtreeFlags & 16384 && n !== null) n.return = t, t = n;
			else {
				if (t === e) break;
				for (; t.sibling === null;) {
					if (t.return === null || t.return === e) return !0;
					t = t.return;
				}
				t.sibling.return = t.return, t = t.sibling;
			}
		}
		return !0;
	}
	function bl(e, t) {
		for (t &= ~Xc, t &= ~Yc, e.suspendedLanes |= t, e.pingedLanes &= ~t, e = e.expirationTimes; 0 < t;) {
			var n = 31 - Tt(t), r = 1 << n;
			e[n] = -1, t &= ~r;
		}
	}
	function xl(e) {
		if ($ & 6) throw Error(r(327));
		Il();
		var t = Mt(e, 0);
		if (!(t & 1)) return hl(e, ht()), null;
		var n = kl(e, t);
		if (e.tag !== 0 && n === 2) {
			var i = Ft(e);
			i !== 0 && (t = i, n = _l(e, i));
		}
		if (n === 1) throw n = qc, Tl(e, 0), bl(e, t), hl(e, ht()), n;
		if (n === 6) throw Error(r(345));
		return e.finishedWork = e.current.alternate, e.finishedLanes = t, Pl(e, Qc, tl), hl(e, ht()), null;
	}
	function Sl(e, t) {
		var n = $;
		$ |= 1;
		try {
			return e(t);
		} finally {
			$ = n, $ === 0 && (el = ht() + 500, ra && sa());
		}
	}
	function Cl(e) {
		ol !== null && ol.tag === 0 && !($ & 6) && Il();
		var t = $;
		$ |= 1;
		var n = Bc.transition, r = V;
		try {
			if (Bc.transition = null, V = 1, e) return e();
		} finally {
			V = r, Bc.transition = n, $ = t, !($ & 6) && sa();
		}
	}
	function wl() {
		Wc = Gc.current, W(Gc);
	}
	function Tl(e, t) {
		e.finishedWork = null, e.finishedLanes = 0;
		var n = e.timeoutHandle;
		if (n !== -1 && (e.timeoutHandle = -1, wi(n)), Hc !== null) for (n = Hc.return; n !== null;) {
			var r = n;
			switch (ba(r), r.tag) {
				case 1:
					r = r.type.childContextTypes, r != null && Zi();
					break;
				case 3:
					mo(), W(qi), W(Ki), yo();
					break;
				case 5:
					go(r);
					break;
				case 4:
					mo();
					break;
				case 13:
					W(J);
					break;
				case 19:
					W(J);
					break;
				case 10:
					Wa(r.type._context);
					break;
				case 22:
				case 23: wl();
			}
			n = n.return;
		}
		if (Vc = e, Hc = e = Yl(e.current, null), Uc = Wc = t, Kc = 0, qc = null, Xc = Yc = Jc = 0, Qc = Zc = null, Ja !== null) {
			for (t = 0; t < Ja.length; t++) if (n = Ja[t], r = n.interleaved, r !== null) {
				n.interleaved = null;
				var i = r.next, a = n.pending;
				if (a !== null) {
					var o = a.next;
					a.next = i, r.next = o;
				}
				n.pending = r;
			}
			Ja = null;
		}
		return e;
	}
	function El(e, t) {
		do {
			var n = Hc;
			try {
				if (Ua(), bo.current = ms, Eo) {
					for (var i = Co.memoizedState; i !== null;) {
						var a = i.queue;
						a !== null && (a.pending = null), i = i.next;
					}
					Eo = !1;
				}
				if (So = 0, To = wo = Co = null, Do = !1, Oo = 0, zc.current = null, n === null || n.return === null) {
					Kc = 1, qc = t, Hc = null;
					break;
				}
				a: {
					var o = e, s = n.return, c = n, l = t;
					if (t = Uc, c.flags |= 32768, typeof l == "object" && l && typeof l.then == "function") {
						var u = l, d = c, f = d.tag;
						if (!(d.mode & 1) && (f === 0 || f === 11 || f === 15)) {
							var p = d.alternate;
							p ? (d.updateQueue = p.updateQueue, d.memoizedState = p.memoizedState, d.lanes = p.lanes) : (d.updateQueue = null, d.memoizedState = null);
						}
						var m = Ms(s);
						if (m !== null) {
							m.flags &= -257, Ns(m, s, c, o, t), m.mode & 1 && js(o, u, t), t = m, l = u;
							var h = t.updateQueue;
							if (h === null) {
								var g = /* @__PURE__ */ new Set();
								g.add(l), t.updateQueue = g;
							} else h.add(l);
							break a;
						} else {
							if (!(t & 1)) {
								js(o, u, t), Ol();
								break a;
							}
							l = Error(r(426));
						}
					} else if (K && c.mode & 1) {
						var _ = Ms(s);
						if (_ !== null) {
							!(_.flags & 65536) && (_.flags |= 256), Ns(_, s, c, o, t), ja(Ts(l, c));
							break a;
						}
					}
					o = l = Ts(l, c), Kc !== 4 && (Kc = 2), Zc === null ? Zc = [o] : Zc.push(o), o = s;
					do {
						switch (o.tag) {
							case 3:
								o.flags |= 65536, t &= -t, o.lanes |= t;
								var v = ks(o, l, t);
								io(o, v);
								break a;
							case 1:
								c = l;
								var y = o.type, b = o.stateNode;
								if (!(o.flags & 128) && (typeof y.getDerivedStateFromError == "function" || b !== null && typeof b.componentDidCatch == "function" && (il === null || !il.has(b)))) {
									o.flags |= 65536, t &= -t, o.lanes |= t;
									var x = As(o, c, t);
									io(o, x);
									break a;
								}
						}
						o = o.return;
					} while (o !== null);
				}
				Nl(n);
			} catch (e) {
				t = e, Hc === n && n !== null && (Hc = n = n.return);
				continue;
			}
			break;
		} while (1);
	}
	function Dl() {
		var e = Rc.current;
		return Rc.current = ms, e === null ? ms : e;
	}
	function Ol() {
		(Kc === 0 || Kc === 3 || Kc === 2) && (Kc = 4), Vc === null || !(Jc & 268435455) && !(Yc & 268435455) || bl(Vc, Uc);
	}
	function kl(e, t) {
		var n = $;
		$ |= 2;
		var i = Dl();
		(Vc !== e || Uc !== t) && (tl = null, Tl(e, t));
		do
			try {
				Al();
				break;
			} catch (t) {
				El(e, t);
			}
		while (1);
		if (Ua(), $ = n, Rc.current = i, Hc !== null) throw Error(r(261));
		return Vc = null, Uc = 0, Kc;
	}
	function Al() {
		for (; Hc !== null;) Ml(Hc);
	}
	function jl() {
		for (; Hc !== null && !pt();) Ml(Hc);
	}
	function Ml(e) {
		var t = Ul(e.alternate, e, Wc);
		e.memoizedProps = e.pendingProps, t === null ? Nl(e) : Hc = t, zc.current = null;
	}
	function Nl(e) {
		var t = e;
		do {
			var n = t.alternate;
			if (e = t.return, t.flags & 32768) {
				if (n = dc(n, t), n !== null) {
					n.flags &= 32767, Hc = n;
					return;
				}
				if (e !== null) e.flags |= 32768, e.subtreeFlags = 0, e.deletions = null;
				else {
					Kc = 6, Hc = null;
					return;
				}
			} else if (n = uc(n, t, Wc), n !== null) {
				Hc = n;
				return;
			}
			if (t = t.sibling, t !== null) {
				Hc = t;
				return;
			}
			Hc = t = e;
		} while (t !== null);
		Kc === 0 && (Kc = 5);
	}
	function Pl(e, t, n) {
		var r = V, i = Bc.transition;
		try {
			Bc.transition = null, V = 1, Fl(e, t, n, r);
		} finally {
			Bc.transition = i, V = r;
		}
		return null;
	}
	function Fl(e, t, n, i) {
		do
			Il();
		while (ol !== null);
		if ($ & 6) throw Error(r(327));
		n = e.finishedWork;
		var a = e.finishedLanes;
		if (n === null) return null;
		if (e.finishedWork = null, e.finishedLanes = 0, n === e.current) throw Error(r(177));
		e.callbackNode = null, e.callbackPriority = 0;
		var o = n.lanes | n.childLanes;
		if (zt(e, o), e === Vc && (Hc = Vc = null, Uc = 0), !(n.subtreeFlags & 2064) && !(n.flags & 2064) || al || (al = !0, Wl(yt, function() {
			return Il(), null;
		})), o = (n.flags & 15990) != 0, n.subtreeFlags & 15990 || o) {
			o = Bc.transition, Bc.transition = null;
			var s = V;
			V = 1;
			var c = $;
			$ |= 4, zc.current = null, hc(e, n), Ac(n, e), Fr(xi), pn = !!bi, xi = bi = null, e.current = n, Mc(n, e, a), mt(), $ = c, V = s, Bc.transition = o;
		} else e.current = n;
		if (al && (al = !1, ol = e, sl = a), o = e.pendingLanes, o === 0 && (il = null), wt(n.stateNode, i), hl(e, ht()), t !== null) for (i = e.onRecoverableError, n = 0; n < t.length; n++) a = t[n], i(a.value, {
			componentStack: a.stack,
			digest: a.digest
		});
		if (nl) throw nl = !1, e = rl, rl = null, e;
		return sl & 1 && e.tag !== 0 && Il(), o = e.pendingLanes, o & 1 ? e === ll ? cl++ : (cl = 0, ll = e) : cl = 0, sa(), null;
	}
	function Il() {
		if (ol !== null) {
			var e = Vt(sl), t = Bc.transition, n = V;
			try {
				if (Bc.transition = null, V = 16 > e ? 16 : e, ol === null) var i = !1;
				else {
					if (e = ol, ol = null, sl = 0, $ & 6) throw Error(r(331));
					var a = $;
					for ($ |= 4, X = e.current; X !== null;) {
						var o = X, s = o.child;
						if (X.flags & 16) {
							var c = o.deletions;
							if (c !== null) {
								for (var l = 0; l < c.length; l++) {
									var u = c[l];
									for (X = u; X !== null;) {
										var d = X;
										switch (d.tag) {
											case 0:
											case 11:
											case 15: gc(8, d, o);
										}
										var f = d.child;
										if (f !== null) f.return = d, X = f;
										else for (; X !== null;) {
											d = X;
											var p = d.sibling, m = d.return;
											if (yc(d), d === u) {
												X = null;
												break;
											}
											if (p !== null) {
												p.return = m, X = p;
												break;
											}
											X = m;
										}
									}
								}
								var h = o.alternate;
								if (h !== null) {
									var g = h.child;
									if (g !== null) {
										h.child = null;
										do {
											var _ = g.sibling;
											g.sibling = null, g = _;
										} while (g !== null);
									}
								}
								X = o;
							}
						}
						if (o.subtreeFlags & 2064 && s !== null) s.return = o, X = s;
						else b: for (; X !== null;) {
							if (o = X, o.flags & 2048) switch (o.tag) {
								case 0:
								case 11:
								case 15: gc(9, o, o.return);
							}
							var v = o.sibling;
							if (v !== null) {
								v.return = o.return, X = v;
								break b;
							}
							X = o.return;
						}
					}
					var y = e.current;
					for (X = y; X !== null;) {
						s = X;
						var b = s.child;
						if (s.subtreeFlags & 2064 && b !== null) b.return = s, X = b;
						else b: for (s = y; X !== null;) {
							if (c = X, c.flags & 2048) try {
								switch (c.tag) {
									case 0:
									case 11:
									case 15: _c(9, c);
								}
							} catch (e) {
								Rl(c, c.return, e);
							}
							if (c === s) {
								X = null;
								break b;
							}
							var x = c.sibling;
							if (x !== null) {
								x.return = c.return, X = x;
								break b;
							}
							X = c.return;
						}
					}
					if ($ = a, sa(), Ct && typeof Ct.onPostCommitFiberRoot == "function") try {
						Ct.onPostCommitFiberRoot(St, e);
					} catch {}
					i = !0;
				}
				return i;
			} finally {
				V = n, Bc.transition = t;
			}
		}
		return !1;
	}
	function Ll(e, t, n) {
		t = Ts(n, t), t = ks(e, t, 1), e = no(e, t, 1), t = fl(), e !== null && (Rt(e, 1, t), hl(e, t));
	}
	function Rl(e, t, n) {
		if (e.tag === 3) Ll(e, e, n);
		else for (; t !== null;) {
			if (t.tag === 3) {
				Ll(t, e, n);
				break;
			} else if (t.tag === 1) {
				var r = t.stateNode;
				if (typeof t.type.getDerivedStateFromError == "function" || typeof r.componentDidCatch == "function" && (il === null || !il.has(r))) {
					e = Ts(n, e), e = As(t, e, 1), t = no(t, e, 1), e = fl(), t !== null && (Rt(t, 1, e), hl(t, e));
					break;
				}
			}
			t = t.return;
		}
	}
	function zl(e, t, n) {
		var r = e.pingCache;
		r !== null && r.delete(t), t = fl(), e.pingedLanes |= e.suspendedLanes & n, Vc === e && (Uc & n) === n && (Kc === 4 || Kc === 3 && (Uc & 130023424) === Uc && 500 > ht() - $c ? Tl(e, 0) : Xc |= n), hl(e, t);
	}
	function Bl(e, t) {
		t === 0 && (e.mode & 1 ? (t = At, At <<= 1, !(At & 130023424) && (At = 4194304)) : t = 1);
		var n = fl();
		e = Za(e, t), e !== null && (Rt(e, t, n), hl(e, n));
	}
	function Vl(e) {
		var t = e.memoizedState, n = 0;
		t !== null && (n = t.retryLane), Bl(e, n);
	}
	function Hl(e, t) {
		var n = 0;
		switch (e.tag) {
			case 13:
				var i = e.stateNode, a = e.memoizedState;
				a !== null && (n = a.retryLane);
				break;
			case 19:
				i = e.stateNode;
				break;
			default: throw Error(r(314));
		}
		i !== null && i.delete(t), Bl(e, n);
	}
	var Ul = function(e, t, n) {
		if (e !== null) if (e.memoizedProps !== t.pendingProps || qi.current) Fs = !0;
		else {
			if ((e.lanes & n) === 0 && !(t.flags & 128)) return Fs = !1, ic(e, t, n);
			Fs = !!(e.flags & 131072);
		}
		else Fs = !1, K && t.flags & 1048576 && va(t, da, t.index);
		switch (t.lanes = 0, t.tag) {
			case 2:
				var i = t.type;
				nc(e, t), e = t.pendingProps;
				var a = Yi(t, Ki.current);
				Ka(t, n), a = Mo(null, t, i, e, a, n);
				var o = No();
				return t.flags |= 1, typeof a == "object" && a && typeof a.render == "function" && a.$$typeof === void 0 ? (t.tag = 1, t.memoizedState = null, t.updateQueue = null, Xi(i) ? (o = !0, ea(t)) : o = !1, t.memoizedState = a.state !== null && a.state !== void 0 ? a.state : null, $a(t), a.updater = bs, t.stateNode = a, a._reactInternals = t, ws(t, i, e, n), t = Ws(null, t, i, !0, o, n)) : (t.tag = 0, K && o && ya(t), Is(null, t, a, n), t = t.child), t;
			case 16:
				i = t.elementType;
				a: {
					switch (nc(e, t), e = t.pendingProps, a = i._init, i = a(i._payload), t.type = i, a = t.tag = Jl(i), e = vs(i, e), a) {
						case 0:
							t = Hs(null, t, i, e, n);
							break a;
						case 1:
							t = Us(null, t, i, e, n);
							break a;
						case 11:
							t = Ls(null, t, i, e, n);
							break a;
						case 14:
							t = Rs(null, t, i, vs(i.type, e), n);
							break a;
					}
					throw Error(r(306, i, ""));
				}
				return t;
			case 0: return i = t.type, a = t.pendingProps, a = t.elementType === i ? a : vs(i, a), Hs(e, t, i, a, n);
			case 1: return i = t.type, a = t.pendingProps, a = t.elementType === i ? a : vs(i, a), Us(e, t, i, a, n);
			case 3:
				a: {
					if (Gs(t), e === null) throw Error(r(387));
					i = t.pendingProps, o = t.memoizedState, a = o.element, eo(e, t), ao(t, i, null, n);
					var s = t.memoizedState;
					if (i = s.element, o.isDehydrated) if (o = {
						element: i,
						isDehydrated: !1,
						cache: s.cache,
						pendingSuspenseBoundaries: s.pendingSuspenseBoundaries,
						transitions: s.transitions
					}, t.updateQueue.baseState = o, t.memoizedState = o, t.flags & 256) {
						a = Ts(Error(r(423)), t), t = Ks(e, t, i, n, a);
						break a;
					} else if (i !== a) {
						a = Ts(Error(r(424)), t), t = Ks(e, t, i, n, a);
						break a;
					} else for (Sa = ki(t.stateNode.containerInfo.firstChild), xa = t, K = !0, Ca = null, n = Ra(t, null, i, n), t.child = n; n;) n.flags = n.flags & -3 | 4096, n = n.sibling;
					else {
						if (Aa(), i === a) {
							t = rc(e, t, n);
							break a;
						}
						Is(e, t, i, n);
					}
					t = t.child;
				}
				return t;
			case 5: return ho(t), e === null && Ea(t), i = t.type, a = t.pendingProps, o = e === null ? null : e.memoizedProps, s = a.children, Si(i, a) ? s = null : o !== null && Si(i, o) && (t.flags |= 32), Vs(e, t), Is(e, t, s, n), t.child;
			case 6: return e === null && Ea(t), null;
			case 13: return Ys(e, t, n);
			case 4: return po(t, t.stateNode.containerInfo), i = t.pendingProps, e === null ? t.child = La(t, null, i, n) : Is(e, t, i, n), t.child;
			case 11: return i = t.type, a = t.pendingProps, a = t.elementType === i ? a : vs(i, a), Ls(e, t, i, a, n);
			case 7: return Is(e, t, t.pendingProps, n), t.child;
			case 8: return Is(e, t, t.pendingProps.children, n), t.child;
			case 12: return Is(e, t, t.pendingProps.children, n), t.child;
			case 10:
				a: {
					if (i = t.type._context, a = t.pendingProps, o = t.memoizedProps, s = a.value, G(za, i._currentValue), i._currentValue = s, o !== null) if (Or(o.value, s)) {
						if (o.children === a.children && !qi.current) {
							t = rc(e, t, n);
							break a;
						}
					} else for (o = t.child, o !== null && (o.return = t); o !== null;) {
						var c = o.dependencies;
						if (c !== null) {
							s = o.child;
							for (var l = c.firstContext; l !== null;) {
								if (l.context === i) {
									if (o.tag === 1) {
										l = to(-1, n & -n), l.tag = 2;
										var u = o.updateQueue;
										if (u !== null) {
											u = u.shared;
											var d = u.pending;
											d === null ? l.next = l : (l.next = d.next, d.next = l), u.pending = l;
										}
									}
									o.lanes |= n, l = o.alternate, l !== null && (l.lanes |= n), Ga(o.return, n, t), c.lanes |= n;
									break;
								}
								l = l.next;
							}
						} else if (o.tag === 10) s = o.type === t.type ? null : o.child;
						else if (o.tag === 18) {
							if (s = o.return, s === null) throw Error(r(341));
							s.lanes |= n, c = s.alternate, c !== null && (c.lanes |= n), Ga(s, n, t), s = o.sibling;
						} else s = o.child;
						if (s !== null) s.return = o;
						else for (s = o; s !== null;) {
							if (s === t) {
								s = null;
								break;
							}
							if (o = s.sibling, o !== null) {
								o.return = s.return, s = o;
								break;
							}
							s = s.return;
						}
						o = s;
					}
					Is(e, t, a.children, n), t = t.child;
				}
				return t;
			case 9: return a = t.type, i = t.pendingProps.children, Ka(t, n), a = qa(a), i = i(a), t.flags |= 1, Is(e, t, i, n), t.child;
			case 14: return i = t.type, a = vs(i, t.pendingProps), a = vs(i.type, a), Rs(e, t, i, a, n);
			case 15: return zs(e, t, t.type, t.pendingProps, n);
			case 17: return i = t.type, a = t.pendingProps, a = t.elementType === i ? a : vs(i, a), nc(e, t), t.tag = 1, Xi(i) ? (e = !0, ea(t)) : e = !1, Ka(t, n), Ss(t, i, a), ws(t, i, a, n), Ws(null, t, i, !0, e, n);
			case 19: return tc(e, t, n);
			case 22: return Bs(e, t, n);
		}
		throw Error(r(156, t.tag));
	};
	function Wl(e, t) {
		return dt(e, t);
	}
	function Gl(e, t, n, r) {
		this.tag = e, this.key = n, this.sibling = this.child = this.return = this.stateNode = this.type = this.elementType = null, this.index = 0, this.ref = null, this.pendingProps = t, this.dependencies = this.memoizedState = this.updateQueue = this.memoizedProps = null, this.mode = r, this.subtreeFlags = this.flags = 0, this.deletions = null, this.childLanes = this.lanes = 0, this.alternate = null;
	}
	function Kl(e, t, n, r) {
		return new Gl(e, t, n, r);
	}
	function ql(e) {
		return e = e.prototype, !(!e || !e.isReactComponent);
	}
	function Jl(e) {
		if (typeof e == "function") return +!!ql(e);
		if (e != null) {
			if (e = e.$$typeof, e === j) return 11;
			if (e === P) return 14;
		}
		return 2;
	}
	function Yl(e, t) {
		var n = e.alternate;
		return n === null ? (n = Kl(e.tag, t, e.key, e.mode), n.elementType = e.elementType, n.type = e.type, n.stateNode = e.stateNode, n.alternate = e, e.alternate = n) : (n.pendingProps = t, n.type = e.type, n.flags = 0, n.subtreeFlags = 0, n.deletions = null), n.flags = e.flags & 14680064, n.childLanes = e.childLanes, n.lanes = e.lanes, n.child = e.child, n.memoizedProps = e.memoizedProps, n.memoizedState = e.memoizedState, n.updateQueue = e.updateQueue, t = e.dependencies, n.dependencies = t === null ? null : {
			lanes: t.lanes,
			firstContext: t.firstContext
		}, n.sibling = e.sibling, n.index = e.index, n.ref = e.ref, n;
	}
	function Xl(e, t, n, i, a, o) {
		var s = 2;
		if (i = e, typeof e == "function") ql(e) && (s = 1);
		else if (typeof e == "string") s = 5;
		else a: switch (e) {
			case E: return Zl(n.children, a, o, t);
			case D:
				s = 8, a |= 8;
				break;
			case O: return e = Kl(12, n, t, a | 2), e.elementType = O, e.lanes = o, e;
			case M: return e = Kl(13, n, t, a), e.elementType = M, e.lanes = o, e;
			case N: return e = Kl(19, n, t, a), e.elementType = N, e.lanes = o, e;
			case I: return Ql(n, a, o, t);
			default:
				if (typeof e == "object" && e) switch (e.$$typeof) {
					case k:
						s = 10;
						break a;
					case A:
						s = 9;
						break a;
					case j:
						s = 11;
						break a;
					case P:
						s = 14;
						break a;
					case F:
						s = 16, i = null;
						break a;
				}
				throw Error(r(130, e == null ? e : typeof e, ""));
		}
		return t = Kl(s, n, t, a), t.elementType = e, t.type = i, t.lanes = o, t;
	}
	function Zl(e, t, n, r) {
		return e = Kl(7, e, r, t), e.lanes = n, e;
	}
	function Ql(e, t, n, r) {
		return e = Kl(22, e, r, t), e.elementType = I, e.lanes = n, e.stateNode = { isHidden: !1 }, e;
	}
	function $l(e, t, n) {
		return e = Kl(6, e, null, t), e.lanes = n, e;
	}
	function eu(e, t, n) {
		return t = Kl(4, e.children === null ? [] : e.children, e.key, t), t.lanes = n, t.stateNode = {
			containerInfo: e.containerInfo,
			pendingChildren: null,
			implementation: e.implementation
		}, t;
	}
	function tu(e, t, n, r, i) {
		this.tag = t, this.containerInfo = e, this.finishedWork = this.pingCache = this.current = this.pendingChildren = null, this.timeoutHandle = -1, this.callbackNode = this.pendingContext = this.context = null, this.callbackPriority = 0, this.eventTimes = Lt(0), this.expirationTimes = Lt(-1), this.entangledLanes = this.finishedLanes = this.mutableReadLanes = this.expiredLanes = this.pingedLanes = this.suspendedLanes = this.pendingLanes = 0, this.entanglements = Lt(0), this.identifierPrefix = r, this.onRecoverableError = i, this.mutableSourceEagerHydrationData = null;
	}
	function nu(e, t, n, r, i, a, o, s, c) {
		return e = new tu(e, t, n, s, c), t === 1 ? (t = 1, !0 === a && (t |= 8)) : t = 0, a = Kl(3, null, null, t), e.current = a, a.stateNode = e, a.memoizedState = {
			element: r,
			isDehydrated: n,
			cache: null,
			transitions: null,
			pendingSuspenseBoundaries: null
		}, $a(a), e;
	}
	function ru(e, t, n) {
		var r = 3 < arguments.length && arguments[3] !== void 0 ? arguments[3] : null;
		return {
			$$typeof: T,
			key: r == null ? null : "" + r,
			children: e,
			containerInfo: t,
			implementation: n
		};
	}
	function iu(e) {
		if (!e) return Gi;
		e = e._reactInternals;
		a: {
			if (at(e) !== e || e.tag !== 1) throw Error(r(170));
			var t = e;
			do {
				switch (t.tag) {
					case 3:
						t = t.stateNode.context;
						break a;
					case 1: if (Xi(t.type)) {
						t = t.stateNode.__reactInternalMemoizedMergedChildContext;
						break a;
					}
				}
				t = t.return;
			} while (t !== null);
			throw Error(r(171));
		}
		if (e.tag === 1) {
			var n = e.type;
			if (Xi(n)) return $i(e, n, t);
		}
		return t;
	}
	function au(e, t, n, r, i, a, o, s, c) {
		return e = nu(n, r, !0, e, i, a, o, s, c), e.context = iu(null), n = e.current, r = fl(), i = pl(n), a = to(r, i), a.callback = t ?? null, no(n, a, i), e.current.lanes = i, Rt(e, i, r), hl(e, r), e;
	}
	function ou(e, t, n, r) {
		var i = t.current, a = fl(), o = pl(i);
		return n = iu(n), t.context === null ? t.context = n : t.pendingContext = n, t = to(a, o), t.payload = { element: e }, r = r === void 0 ? null : r, r !== null && (t.callback = r), e = no(i, t, o), e !== null && (ml(e, i, o, a), ro(e, i, o)), o;
	}
	function su(e) {
		if (e = e.current, !e.child) return null;
		switch (e.child.tag) {
			case 5: return e.child.stateNode;
			default: return e.child.stateNode;
		}
	}
	function cu(e, t) {
		if (e = e.memoizedState, e !== null && e.dehydrated !== null) {
			var n = e.retryLane;
			e.retryLane = n !== 0 && n < t ? n : t;
		}
	}
	function lu(e, t) {
		cu(e, t), (e = e.alternate) && cu(e, t);
	}
	function uu() {
		return null;
	}
	var du = typeof reportError == "function" ? reportError : function(e) {
		console.error(e);
	};
	function fu(e) {
		this._internalRoot = e;
	}
	pu.prototype.render = fu.prototype.render = function(e) {
		var t = this._internalRoot;
		if (t === null) throw Error(r(409));
		ou(e, t, null, null);
	}, pu.prototype.unmount = fu.prototype.unmount = function() {
		var e = this._internalRoot;
		if (e !== null) {
			this._internalRoot = null;
			var t = e.containerInfo;
			Cl(function() {
				ou(null, e, null, null);
			}), t[Pi] = null;
		}
	};
	function pu(e) {
		this._internalRoot = e;
	}
	pu.prototype.unstable_scheduleHydration = function(e) {
		if (e) {
			var t = Gt();
			e = {
				blockedOn: null,
				target: e,
				priority: t
			};
			for (var n = 0; n < en.length && t !== 0 && t < en[n].priority; n++);
			en.splice(n, 0, e), n === 0 && on(e);
		}
	};
	function mu(e) {
		return !(!e || e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11);
	}
	function hu(e) {
		return !(!e || e.nodeType !== 1 && e.nodeType !== 9 && e.nodeType !== 11 && (e.nodeType !== 8 || e.nodeValue !== " react-mount-point-unstable "));
	}
	function gu() {}
	function _u(e, t, n, r, i) {
		if (i) {
			if (typeof r == "function") {
				var a = r;
				r = function() {
					var e = su(o);
					a.call(e);
				};
			}
			var o = au(t, r, e, 0, null, !1, !1, "", gu);
			return e._reactRootContainer = o, e[Pi] = o.current, ci(e.nodeType === 8 ? e.parentNode : e), Cl(), o;
		}
		for (; i = e.lastChild;) e.removeChild(i);
		if (typeof r == "function") {
			var s = r;
			r = function() {
				var e = su(c);
				s.call(e);
			};
		}
		var c = nu(e, 0, !1, null, null, !1, !1, "", gu);
		return e._reactRootContainer = c, e[Pi] = c.current, ci(e.nodeType === 8 ? e.parentNode : e), Cl(function() {
			ou(t, c, n, r);
		}), c;
	}
	function vu(e, t, n, r, i) {
		var a = n._reactRootContainer;
		if (a) {
			var o = a;
			if (typeof i == "function") {
				var s = i;
				i = function() {
					var e = su(o);
					s.call(e);
				};
			}
			ou(t, o, e, i);
		} else o = _u(n, t, e, i, r);
		return su(o);
	}
	Ht = function(e) {
		switch (e.tag) {
			case 3:
				var t = e.stateNode;
				if (t.current.memoizedState.isDehydrated) {
					var n = jt(t.pendingLanes);
					n !== 0 && (Bt(t, n | 1), hl(t, ht()), !($ & 6) && (el = ht() + 500, sa()));
				}
				break;
			case 13: Cl(function() {
				var t = Za(e, 1);
				t !== null && ml(t, e, 1, fl());
			}), lu(e, 1);
		}
	}, Ut = function(e) {
		if (e.tag === 13) {
			var t = Za(e, 134217728);
			t !== null && ml(t, e, 134217728, fl()), lu(e, 134217728);
		}
	}, Wt = function(e) {
		if (e.tag === 13) {
			var t = pl(e), n = Za(e, t);
			n !== null && ml(n, e, t, fl()), lu(e, t);
		}
	}, Gt = function() {
		return V;
	}, Kt = function(e, t) {
		var n = V;
		try {
			return V = e, t();
		} finally {
			V = n;
		}
	}, Re = function(e, t, n) {
		switch (t) {
			case "input":
				if (he(e, n), t = n.name, n.type === "radio" && t != null) {
					for (n = e; n.parentNode;) n = n.parentNode;
					for (n = n.querySelectorAll("input[name=" + JSON.stringify("" + t) + "][type=\"radio\"]"), t = 0; t < n.length; t++) {
						var i = n[t];
						if (i !== e && i.form === e.form) {
							var a = Vi(i);
							if (!a) throw Error(r(90));
							ue(i), he(i, a);
						}
					}
				}
				break;
			case "textarea":
				Se(e, n);
				break;
			case "select": t = n.value, t != null && ye(e, !!n.multiple, t, !1);
		}
	}, We = Sl, Ge = Cl;
	var yu = {
		usingClientEntryPoint: !1,
		Events: [
			zi,
			Bi,
			Vi,
			He,
			Ue,
			Sl
		]
	}, bu = {
		findFiberByHostInstance: Ri,
		bundleType: 0,
		version: "18.3.1",
		rendererPackageName: "react-dom"
	}, xu = {
		bundleType: bu.bundleType,
		version: bu.version,
		rendererPackageName: bu.rendererPackageName,
		rendererConfig: bu.rendererConfig,
		overrideHookState: null,
		overrideHookStateDeletePath: null,
		overrideHookStateRenamePath: null,
		overrideProps: null,
		overridePropsDeletePath: null,
		overridePropsRenamePath: null,
		setErrorHandler: null,
		setSuspenseHandler: null,
		scheduleUpdate: null,
		currentDispatcherRef: C.ReactCurrentDispatcher,
		findHostInstanceByFiber: function(e) {
			return e = lt(e), e === null ? null : e.stateNode;
		},
		findFiberByHostInstance: bu.findFiberByHostInstance || uu,
		findHostInstancesForRefresh: null,
		scheduleRefresh: null,
		scheduleRoot: null,
		setRefreshHandler: null,
		getCurrentFiber: null,
		reconcilerVersion: "18.3.1-next-f1338f8080-20240426"
	};
	if (typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ < "u") {
		var Su = __REACT_DEVTOOLS_GLOBAL_HOOK__;
		if (!Su.isDisabled && Su.supportsFiber) try {
			St = Su.inject(xu), Ct = Su;
		} catch {}
	}
	e.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED = yu, e.createPortal = function(e, t) {
		var n = 2 < arguments.length && arguments[2] !== void 0 ? arguments[2] : null;
		if (!mu(t)) throw Error(r(200));
		return ru(e, t, null, n);
	}, e.createRoot = function(e, t) {
		if (!mu(e)) throw Error(r(299));
		var n = !1, i = "", a = du;
		return t != null && (!0 === t.unstable_strictMode && (n = !0), t.identifierPrefix !== void 0 && (i = t.identifierPrefix), t.onRecoverableError !== void 0 && (a = t.onRecoverableError)), t = nu(e, 1, !1, null, null, n, !1, i, a), e[Pi] = t.current, ci(e.nodeType === 8 ? e.parentNode : e), new fu(t);
	}, e.findDOMNode = function(e) {
		if (e == null) return null;
		if (e.nodeType === 1) return e;
		var t = e._reactInternals;
		if (t === void 0) throw typeof e.render == "function" ? Error(r(188)) : (e = Object.keys(e).join(","), Error(r(268, e)));
		return e = lt(t), e = e === null ? null : e.stateNode, e;
	}, e.flushSync = function(e) {
		return Cl(e);
	}, e.hydrate = function(e, t, n) {
		if (!hu(t)) throw Error(r(200));
		return vu(null, e, t, !0, n);
	}, e.hydrateRoot = function(e, t, n) {
		if (!mu(e)) throw Error(r(405));
		var i = n != null && n.hydratedSources || null, a = !1, o = "", s = du;
		if (n != null && (!0 === n.unstable_strictMode && (a = !0), n.identifierPrefix !== void 0 && (o = n.identifierPrefix), n.onRecoverableError !== void 0 && (s = n.onRecoverableError)), t = au(t, null, e, 1, n ?? null, a, !1, o, s), e[Pi] = t.current, ci(e), i) for (e = 0; e < i.length; e++) n = i[e], a = n._getVersion, a = a(n._source), t.mutableSourceEagerHydrationData == null ? t.mutableSourceEagerHydrationData = [n, a] : t.mutableSourceEagerHydrationData.push(n, a);
		return new pu(t);
	}, e.render = function(e, t, n) {
		if (!hu(t)) throw Error(r(200));
		return vu(null, e, t, !1, n);
	}, e.unmountComponentAtNode = function(e) {
		if (!hu(e)) throw Error(r(40));
		return e._reactRootContainer ? (Cl(function() {
			vu(null, null, e, !1, function() {
				e._reactRootContainer = null, e[Pi] = null;
			});
		}), !0) : !1;
	}, e.unstable_batchedUpdates = Sl, e.unstable_renderSubtreeIntoContainer = function(e, t, n, i) {
		if (!hu(n)) throw Error(r(200));
		if (e == null || e._reactInternals === void 0) throw Error(r(38));
		return vu(e, t, n, !1, i);
	}, e.version = "18.3.1-next-f1338f8080-20240426";
})), m = /* @__PURE__ */ o(((e, t) => {
	function n() {
		if (!(typeof __REACT_DEVTOOLS_GLOBAL_HOOK__ > "u" || typeof __REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE != "function")) try {
			__REACT_DEVTOOLS_GLOBAL_HOOK__.checkDCE(n);
		} catch (e) {
			console.error(e);
		}
	}
	n(), t.exports = p();
})), h = (/* @__PURE__ */ o(((e) => {
	var t = m();
	e.createRoot = t.createRoot, e.hydrateRoot = t.hydrateRoot;
})))(), g = ".react-flow{--xy-edge-stroke-default:#b1b1b7;--xy-edge-stroke-width-default:1;--xy-edge-stroke-selected-default:#555;--xy-connectionline-stroke-default:#b1b1b7;--xy-connectionline-stroke-width-default:1;--xy-attribution-background-color-default:#ffffff80;--xy-minimap-background-color-default:#fff;--xy-minimap-mask-background-color-default:#f0f0f099;--xy-minimap-mask-stroke-color-default:transparent;--xy-minimap-mask-stroke-width-default:1;--xy-minimap-node-background-color-default:#e2e2e2;--xy-minimap-node-stroke-color-default:transparent;--xy-minimap-node-stroke-width-default:2;--xy-background-color-default:transparent;--xy-background-pattern-dots-color-default:#91919a;--xy-background-pattern-lines-color-default:#eee;--xy-background-pattern-cross-color-default:#e2e2e2;background-color:var(--xy-background-color,var(--xy-background-color-default));--xy-node-color-default:inherit;--xy-node-border-default:1px solid #1a192b;--xy-node-background-color-default:#fff;--xy-node-group-background-color-default:#f0f0f040;--xy-node-boxshadow-hover-default:0 1px 4px 1px #00000014;--xy-node-boxshadow-selected-default:0 0 0 .5px #1a192b;--xy-node-border-radius-default:3px;--xy-handle-background-color-default:#1a192b;--xy-handle-border-color-default:#fff;--xy-selection-background-color-default:#0059dc14;--xy-selection-border-default:1px dotted #0059dccc;--xy-controls-button-background-color-default:#fefefe;--xy-controls-button-background-color-hover-default:#f4f4f4;--xy-controls-button-color-default:inherit;--xy-controls-button-color-hover-default:inherit;--xy-controls-button-border-color-default:#eee;--xy-controls-box-shadow-default:0 0 2px 1px #00000014;--xy-edge-label-background-color-default:#fff;--xy-edge-label-color-default:inherit;--xy-resize-background-color-default:#3367d9;direction:ltr}.react-flow.dark{--xy-edge-stroke-default:#3e3e3e;--xy-edge-stroke-width-default:1;--xy-edge-stroke-selected-default:#727272;--xy-connectionline-stroke-default:#b1b1b7;--xy-connectionline-stroke-width-default:1;--xy-attribution-background-color-default:#96969640;--xy-minimap-background-color-default:#141414;--xy-minimap-mask-background-color-default:#3c3c3c99;--xy-minimap-mask-stroke-color-default:transparent;--xy-minimap-mask-stroke-width-default:1;--xy-minimap-node-background-color-default:#2b2b2b;--xy-minimap-node-stroke-color-default:transparent;--xy-minimap-node-stroke-width-default:2;--xy-background-color-default:#141414;--xy-background-pattern-dots-color-default:#777;--xy-background-pattern-lines-color-default:#777;--xy-background-pattern-cross-color-default:#777;--xy-node-color-default:#f8f8f8;--xy-node-border-default:1px solid #3c3c3c;--xy-node-background-color-default:#1e1e1e;--xy-node-group-background-color-default:#f0f0f040;--xy-node-boxshadow-hover-default:0 1px 4px 1px #ffffff14;--xy-node-boxshadow-selected-default:0 0 0 .5px #999;--xy-handle-background-color-default:#bebebe;--xy-handle-border-color-default:#1e1e1e;--xy-selection-background-color-default:#c8c8dc14;--xy-selection-border-default:1px dotted #c8c8dccc;--xy-controls-button-background-color-default:#2b2b2b;--xy-controls-button-background-color-hover-default:#3e3e3e;--xy-controls-button-color-default:#f8f8f8;--xy-controls-button-color-hover-default:#fff;--xy-controls-button-border-color-default:#5b5b5b;--xy-controls-box-shadow-default:0 0 2px 1px #00000014;--xy-edge-label-background-color-default:#141414;--xy-edge-label-color-default:#f8f8f8}.react-flow__background{background-color:var(--xy-background-color-props,var(--xy-background-color,var(--xy-background-color-default)));pointer-events:none;z-index:-1}.react-flow__container{width:100%;height:100%;position:absolute;top:0;left:0}.react-flow__pane{z-index:1;touch-action:none}.react-flow__pane.draggable{cursor:grab}.react-flow__pane.dragging{cursor:grabbing}.react-flow__pane.selection{cursor:pointer}.react-flow__viewport{transform-origin:0 0;z-index:2;pointer-events:none}.react-flow__renderer{z-index:4}.react-flow__selection{z-index:6}.react-flow__nodesselection-rect:focus,.react-flow__nodesselection-rect:focus-visible{outline:none}.react-flow__edge-path{stroke:var(--xy-edge-stroke,var(--xy-edge-stroke-default));stroke-width:var(--xy-edge-stroke-width,var(--xy-edge-stroke-width-default));fill:none}.react-flow__connection-path{stroke:var(--xy-connectionline-stroke,var(--xy-connectionline-stroke-default));stroke-width:var(--xy-connectionline-stroke-width,var(--xy-connectionline-stroke-width-default));fill:none}.react-flow .react-flow__edges{position:absolute}.react-flow .react-flow__edges svg{pointer-events:none;position:absolute;overflow:visible}.react-flow__edge{pointer-events:visibleStroke}.react-flow__edge.selectable{cursor:pointer}.react-flow__edge.animated path{stroke-dasharray:5;animation:.5s linear infinite dashdraw}.react-flow__edge.animated path.react-flow__edge-interaction{stroke-dasharray:none;animation:none}.react-flow__edge.inactive{pointer-events:none}.react-flow__edge.selected,.react-flow__edge:focus,.react-flow__edge:focus-visible{outline:none}.react-flow__edge.selected .react-flow__edge-path,.react-flow__edge.selectable:focus .react-flow__edge-path,.react-flow__edge.selectable:focus-visible .react-flow__edge-path{stroke:var(--xy-edge-stroke-selected,var(--xy-edge-stroke-selected-default))}.react-flow__edge-textwrapper{pointer-events:all}.react-flow__edge .react-flow__edge-text{pointer-events:none;-webkit-user-select:none;user-select:none}.react-flow__arrowhead polyline{stroke:var(--xy-edge-stroke,var(--xy-edge-stroke-default))}.react-flow__arrowhead polyline.arrowclosed{fill:var(--xy-edge-stroke,var(--xy-edge-stroke-default))}.react-flow__connection{pointer-events:none}.react-flow__connection .animated{stroke-dasharray:5;animation:.5s linear infinite dashdraw}svg.react-flow__connectionline{z-index:1001;position:absolute;overflow:visible}.react-flow__nodes{pointer-events:none;transform-origin:0 0}.react-flow__node{-webkit-user-select:none;user-select:none;pointer-events:all;transform-origin:0 0;box-sizing:border-box;cursor:default;position:absolute}.react-flow__node.selectable{cursor:pointer}.react-flow__node.draggable{cursor:grab;pointer-events:all}.react-flow__node.draggable.dragging{cursor:grabbing}.react-flow__nodesselection{z-index:3;transform-origin:0 0;pointer-events:none}.react-flow__nodesselection-rect{pointer-events:all;cursor:grab;position:absolute}.react-flow__handle{pointer-events:none;background-color:var(--xy-handle-background-color,var(--xy-handle-background-color-default));border:1px solid var(--xy-handle-border-color,var(--xy-handle-border-color-default));border-radius:100%;width:6px;min-width:5px;height:6px;min-height:5px;position:absolute}.react-flow__handle.connectingfrom{pointer-events:all}.react-flow__handle.connectionindicator{pointer-events:all;cursor:crosshair}.react-flow__handle-bottom{top:auto;bottom:0;left:50%;transform:translate(-50%,50%)}.react-flow__handle-top{top:0;left:50%;transform:translate(-50%,-50%)}.react-flow__handle-left{top:50%;left:0;transform:translate(-50%,-50%)}.react-flow__handle-right{top:50%;right:0;transform:translate(50%,-50%)}.react-flow__edgeupdater{cursor:move;pointer-events:all}.react-flow__pane.selection .react-flow__panel{pointer-events:none}.react-flow__panel{z-index:5;margin:15px;position:absolute}.react-flow__panel.top{top:0}.react-flow__panel.bottom{bottom:0}.react-flow__panel.top.center,.react-flow__panel.bottom.center{left:50%;transform:translate(-15px)translate(-50%)}.react-flow__panel.left{left:0}.react-flow__panel.right{right:0}.react-flow__panel.left.center,.react-flow__panel.right.center{top:50%;transform:translateY(-15px)translateY(-50%)}.react-flow__attribution{background:var(--xy-attribution-background-color,var(--xy-attribution-background-color-default));margin:0;padding:2px 3px;font-size:10px}.react-flow__attribution a{color:#999;text-decoration:none}@keyframes dashdraw{0%{stroke-dashoffset:10px}}.react-flow__edgelabel-renderer{pointer-events:none;-webkit-user-select:none;user-select:none;width:100%;height:100%;position:absolute;top:0;left:0}.react-flow__viewport-portal{-webkit-user-select:none;user-select:none;width:100%;height:100%;position:absolute;top:0;left:0}.react-flow__minimap{background:var(--xy-minimap-background-color-props,var(--xy-minimap-background-color,var(--xy-minimap-background-color-default)))}.react-flow__minimap-svg{display:block}.react-flow__minimap-mask{fill:var(--xy-minimap-mask-background-color-props,var(--xy-minimap-mask-background-color,var(--xy-minimap-mask-background-color-default)));stroke:var(--xy-minimap-mask-stroke-color-props,var(--xy-minimap-mask-stroke-color,var(--xy-minimap-mask-stroke-color-default)));stroke-width:var(--xy-minimap-mask-stroke-width-props,var(--xy-minimap-mask-stroke-width,var(--xy-minimap-mask-stroke-width-default)))}.react-flow__minimap-node{fill:var(--xy-minimap-node-background-color-props,var(--xy-minimap-node-background-color,var(--xy-minimap-node-background-color-default)));stroke:var(--xy-minimap-node-stroke-color-props,var(--xy-minimap-node-stroke-color,var(--xy-minimap-node-stroke-color-default)));stroke-width:var(--xy-minimap-node-stroke-width-props,var(--xy-minimap-node-stroke-width,var(--xy-minimap-node-stroke-width-default)))}.react-flow__background-pattern.dots{fill:var(--xy-background-pattern-color-props,var(--xy-background-pattern-color,var(--xy-background-pattern-dots-color-default)))}.react-flow__background-pattern.lines{stroke:var(--xy-background-pattern-color-props,var(--xy-background-pattern-color,var(--xy-background-pattern-lines-color-default)))}.react-flow__background-pattern.cross{stroke:var(--xy-background-pattern-color-props,var(--xy-background-pattern-color,var(--xy-background-pattern-cross-color-default)))}.react-flow__controls{box-shadow:var(--xy-controls-box-shadow,var(--xy-controls-box-shadow-default));flex-direction:column;display:flex}.react-flow__controls.horizontal{flex-direction:row}.react-flow__controls-button{background:var(--xy-controls-button-background-color,var(--xy-controls-button-background-color-default));border:none;border-bottom:1px solid var(--xy-controls-button-border-color-props,var(--xy-controls-button-border-color,var(--xy-controls-button-border-color-default)));width:26px;height:26px;color:var(--xy-controls-button-color-props,var(--xy-controls-button-color,var(--xy-controls-button-color-default)));cursor:pointer;-webkit-user-select:none;user-select:none;justify-content:center;align-items:center;padding:4px;display:flex}.react-flow__controls-button svg{fill:currentColor;width:100%;max-width:12px;max-height:12px}.react-flow__edge.updating .react-flow__edge-path{stroke:#777}.react-flow__edge-text{font-size:10px}.react-flow__node.selectable:focus,.react-flow__node.selectable:focus-visible{outline:none}.react-flow__node-input,.react-flow__node-default,.react-flow__node-output,.react-flow__node-group{border-radius:var(--xy-node-border-radius,var(--xy-node-border-radius-default));width:150px;color:var(--xy-node-color,var(--xy-node-color-default));text-align:center;border:var(--xy-node-border,var(--xy-node-border-default));background-color:var(--xy-node-background-color,var(--xy-node-background-color-default));padding:10px;font-size:12px}.react-flow__node-input.selectable:hover,.react-flow__node-default.selectable:hover,.react-flow__node-output.selectable:hover,.react-flow__node-group.selectable:hover{box-shadow:var(--xy-node-boxshadow-hover,var(--xy-node-boxshadow-hover-default))}.react-flow__node-input.selectable.selected,.react-flow__node-input.selectable:focus,.react-flow__node-input.selectable:focus-visible,.react-flow__node-default.selectable.selected,.react-flow__node-default.selectable:focus,.react-flow__node-default.selectable:focus-visible,.react-flow__node-output.selectable.selected,.react-flow__node-output.selectable:focus,.react-flow__node-output.selectable:focus-visible,.react-flow__node-group.selectable.selected,.react-flow__node-group.selectable:focus,.react-flow__node-group.selectable:focus-visible{box-shadow:var(--xy-node-boxshadow-selected,var(--xy-node-boxshadow-selected-default))}.react-flow__node-group{background-color:var(--xy-node-group-background-color,var(--xy-node-group-background-color-default))}.react-flow__nodesselection-rect,.react-flow__selection{background:var(--xy-selection-background-color,var(--xy-selection-background-color-default));border:var(--xy-selection-border,var(--xy-selection-border-default))}.react-flow__nodesselection-rect:focus,.react-flow__nodesselection-rect:focus-visible,.react-flow__selection:focus,.react-flow__selection:focus-visible{outline:none}.react-flow__controls-button:hover{background:var(--xy-controls-button-background-color-hover-props,var(--xy-controls-button-background-color-hover,var(--xy-controls-button-background-color-hover-default)));color:var(--xy-controls-button-color-hover-props,var(--xy-controls-button-color-hover,var(--xy-controls-button-color-hover-default)))}.react-flow__controls-button:disabled{pointer-events:none}.react-flow__controls-button:disabled svg{fill-opacity:.4}.react-flow__controls-button:last-child{border-bottom:none}.react-flow__controls.horizontal .react-flow__controls-button{border-bottom:none;border-right:1px solid var(--xy-controls-button-border-color-props,var(--xy-controls-button-border-color,var(--xy-controls-button-border-color-default)))}.react-flow__controls.horizontal .react-flow__controls-button:last-child{border-right:none}.react-flow__resize-control{position:absolute}.react-flow__resize-control.left,.react-flow__resize-control.right{cursor:ew-resize}.react-flow__resize-control.top,.react-flow__resize-control.bottom{cursor:ns-resize}.react-flow__resize-control.top.left,.react-flow__resize-control.bottom.right{cursor:nwse-resize}.react-flow__resize-control.bottom.left,.react-flow__resize-control.top.right{cursor:nesw-resize}.react-flow__resize-control.handle{background-color:var(--xy-resize-background-color,var(--xy-resize-background-color-default));border:1px solid #fff;border-radius:1px;width:5px;height:5px;translate:-50% -50%}.react-flow__resize-control.handle.left{top:50%;left:0}.react-flow__resize-control.handle.right{top:50%;left:100%}.react-flow__resize-control.handle.top{top:0;left:50%}.react-flow__resize-control.handle.bottom{top:100%;left:50%}.react-flow__resize-control.handle.top.left,.react-flow__resize-control.handle.bottom.left{left:0}.react-flow__resize-control.handle.top.right,.react-flow__resize-control.handle.bottom.right{left:100%}.react-flow__resize-control.line{border-color:var(--xy-resize-background-color,var(--xy-resize-background-color-default));border-style:solid;border-width:0}.react-flow__resize-control.line.left,.react-flow__resize-control.line.right{width:1px;height:100%;top:0;transform:translate(-50%)}.react-flow__resize-control.line.left{border-left-width:1px;left:0}.react-flow__resize-control.line.right{border-right-width:1px;left:100%}.react-flow__resize-control.line.top,.react-flow__resize-control.line.bottom{width:100%;height:1px;left:0;transform:translateY(-50%)}.react-flow__resize-control.line.top{border-top-width:1px;top:0}.react-flow__resize-control.line.bottom{border-bottom-width:1px;top:100%}.react-flow__edge-textbg{fill:var(--xy-edge-label-background-color,var(--xy-edge-label-background-color-default))}.react-flow__edge-text{fill:var(--xy-edge-label-color,var(--xy-edge-label-color-default))}", _ = "*,:before,:after,::backdrop{--tw-border-spacing-x:0;--tw-border-spacing-y:0;--tw-translate-x:0;--tw-translate-y:0;--tw-rotate:0;--tw-skew-x:0;--tw-skew-y:0;--tw-scale-x:1;--tw-scale-y:1;--tw-pan-x: ;--tw-pan-y: ;--tw-pinch-zoom: ;--tw-scroll-snap-strictness:proximity;--tw-gradient-from-position: ;--tw-gradient-via-position: ;--tw-gradient-to-position: ;--tw-ordinal: ;--tw-slashed-zero: ;--tw-numeric-figure: ;--tw-numeric-spacing: ;--tw-numeric-fraction: ;--tw-ring-inset: ;--tw-ring-offset-width:0px;--tw-ring-offset-color:#fff;--tw-ring-color:#3b82f680;--tw-ring-offset-shadow:0 0 #0000;--tw-ring-shadow:0 0 #0000;--tw-shadow:0 0 #0000;--tw-shadow-colored:0 0 #0000;--tw-blur: ;--tw-brightness: ;--tw-contrast: ;--tw-grayscale: ;--tw-hue-rotate: ;--tw-invert: ;--tw-saturate: ;--tw-sepia: ;--tw-drop-shadow: ;--tw-backdrop-blur: ;--tw-backdrop-brightness: ;--tw-backdrop-contrast: ;--tw-backdrop-grayscale: ;--tw-backdrop-hue-rotate: ;--tw-backdrop-invert: ;--tw-backdrop-opacity: ;--tw-backdrop-saturate: ;--tw-backdrop-sepia: ;--tw-contain-size: ;--tw-contain-layout: ;--tw-contain-paint: ;--tw-contain-style: }*,:before,:after{box-sizing:border-box;border:0 solid #e5e7eb}:before,:after{--tw-content:\"\"}html,:host{-webkit-text-size-adjust:100%;tab-size:4;font-feature-settings:normal;font-variation-settings:normal;-webkit-tap-highlight-color:transparent;font-family:ui-sans-serif,system-ui,sans-serif,Apple Color Emoji,Segoe UI Emoji,Segoe UI Symbol,Noto Color Emoji;line-height:1.5}body{line-height:inherit;margin:0}hr{height:0;color:inherit;border-top-width:1px}abbr:where([title]){-webkit-text-decoration:underline dotted;text-decoration:underline dotted}h1,h2,h3,h4,h5,h6{font-size:inherit;font-weight:inherit}a{color:inherit;-webkit-text-decoration:inherit;text-decoration:inherit}b,strong{font-weight:bolder}code,kbd,samp,pre{font-feature-settings:normal;font-variation-settings:normal;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,Courier New,monospace;font-size:1em}small{font-size:80%}sub,sup{vertical-align:baseline;font-size:75%;line-height:0;position:relative}sub{bottom:-.25em}sup{top:-.5em}table{text-indent:0;border-color:inherit;border-collapse:collapse}button,input,optgroup,select,textarea{font-feature-settings:inherit;font-variation-settings:inherit;font-family:inherit;font-size:100%;font-weight:inherit;line-height:inherit;letter-spacing:inherit;color:inherit;margin:0;padding:0}button,select{text-transform:none}button,input:where([type=button]),input:where([type=reset]),input:where([type=submit]){-webkit-appearance:button;background-color:#0000;background-image:none}:-moz-focusring{outline:auto}:-moz-ui-invalid{box-shadow:none}progress{vertical-align:baseline}::-webkit-inner-spin-button{height:auto}::-webkit-outer-spin-button{height:auto}[type=search]{-webkit-appearance:textfield;outline-offset:-2px}::-webkit-search-decoration{-webkit-appearance:none}::-webkit-file-upload-button{-webkit-appearance:button;font:inherit}summary{display:list-item}blockquote,dl,dd,h1,h2,h3,h4,h5,h6,hr,figure,p,pre{margin:0}fieldset{margin:0;padding:0}legend{padding:0}ol,ul,menu{margin:0;padding:0;list-style:none}dialog{padding:0}textarea{resize:vertical}input::-moz-placeholder{opacity:1;color:#9ca3af}textarea::-moz-placeholder{opacity:1;color:#9ca3af}input::placeholder,textarea::placeholder{opacity:1;color:#9ca3af}button,[role=button]{cursor:pointer}:disabled{cursor:default}img,svg,video,canvas,audio,iframe,embed,object{vertical-align:middle;display:block}img,video{max-width:100%;height:auto}[hidden]:where(:not([hidden=until-found])){display:none}.\\!container{width:100%!important}.container{width:100%}@media (width>=640px){.\\!container{max-width:640px!important}.container{max-width:640px}}@media (width>=768px){.\\!container{max-width:768px!important}.container{max-width:768px}}@media (width>=1024px){.\\!container{max-width:1024px!important}.container{max-width:1024px}}@media (width>=1280px){.\\!container{max-width:1280px!important}.container{max-width:1280px}}@media (width>=1536px){.\\!container{max-width:1536px!important}.container{max-width:1536px}}.visible{visibility:visible}.collapse{visibility:collapse}.static{position:static}.fixed{position:fixed}.absolute{position:absolute}.relative{position:relative}.sticky{position:sticky}.inset-0{inset:0}.inset-3{inset:.75rem}.inset-6{inset:1.5rem}.bottom-32{bottom:8rem}.bottom-40{bottom:10rem}.left-0{left:0}.left-1\\/2{left:50%}.left-3{left:.75rem}.right-0{right:0}.right-2{right:.5rem}.right-24{right:6rem}.right-3{right:.75rem}.top-0{top:0}.top-1{top:.25rem}.top-3{top:.75rem}.top-7{top:1.75rem}.top-9{top:2.25rem}.top-full{top:100%}.z-10{z-index:10}.z-20{z-index:20}.z-40{z-index:40}.z-50{z-index:50}.z-\\[100\\]{z-index:100}.z-\\[80\\]{z-index:80}.z-\\[9998\\]{z-index:9998}.z-\\[9999\\]{z-index:9999}.order-first{order:-9999}.mx-auto{margin-left:auto;margin-right:auto}.my-1{margin-top:.25rem;margin-bottom:.25rem}.mb-1{margin-bottom:.25rem}.mb-2{margin-bottom:.5rem}.mb-3{margin-bottom:.75rem}.mb-4{margin-bottom:1rem}.ml-1{margin-left:.25rem}.ml-2{margin-left:.5rem}.ml-4{margin-left:1rem}.ml-44{margin-left:11rem}.ml-5{margin-left:1.25rem}.ml-auto{margin-left:auto}.mr-1{margin-right:.25rem}.mr-4{margin-right:1rem}.mt-0\\.5{margin-top:.125rem}.mt-1{margin-top:.25rem}.mt-1\\.5{margin-top:.375rem}.mt-2{margin-top:.5rem}.mt-3{margin-top:.75rem}.mt-4{margin-top:1rem}.mt-5{margin-top:1.25rem}.mt-8{margin-top:2rem}.mt-\\[3px\\]{margin-top:3px}.line-clamp-2{-webkit-line-clamp:2;-webkit-box-orient:vertical;display:-webkit-box;overflow:hidden}.block{display:block}.inline-block{display:inline-block}.inline{display:inline}.flex{display:flex}.inline-flex{display:inline-flex}.table{display:table}.grid{display:grid}.hidden{display:none}.h-0\\.5{height:.125rem}.h-1{height:.25rem}.h-1\\.5{height:.375rem}.h-10{height:2.5rem}.h-2{height:.5rem}.h-2\\.5{height:.625rem}.h-28{height:7rem}.h-3{height:.75rem}.h-3\\.5{height:.875rem}.h-4{height:1rem}.h-6{height:1.5rem}.h-7{height:1.75rem}.h-80{height:20rem}.h-9{height:2.25rem}.h-full{height:100%}.h-screen{height:100vh}.max-h-24{max-height:6rem}.max-h-32{max-height:8rem}.max-h-36{max-height:9rem}.max-h-40{max-height:10rem}.max-h-48{max-height:12rem}.max-h-60{max-height:15rem}.max-h-64{max-height:16rem}.max-h-72{max-height:18rem}.max-h-\\[90vh\\]{max-height:90vh}.max-h-\\[calc\\(100vh-1rem\\)\\]{max-height:calc(100vh - 1rem)}.max-h-full{max-height:100%}.min-h-0{min-height:0}.min-h-14{min-height:3.5rem}.w-1\\/2{width:50%}.w-1\\/4{width:25%}.w-12{width:3rem}.w-16{width:4rem}.w-2{width:.5rem}.w-2\\.5{width:.625rem}.w-20{width:5rem}.w-24{width:6rem}.w-28{width:7rem}.w-3{width:.75rem}.w-3\\.5{width:.875rem}.w-32{width:8rem}.w-4{width:1rem}.w-40{width:10rem}.w-44{width:11rem}.w-60{width:15rem}.w-64{width:16rem}.w-72{width:18rem}.w-80{width:20rem}.w-\\[min\\(30rem\\,calc\\(100\\%-2rem\\)\\)\\]{width:min(30rem,100% - 2rem)}.w-\\[min\\(32rem\\,calc\\(100\\%-2rem\\)\\)\\]{width:min(32rem,100% - 2rem)}.w-full{width:100%}.w-screen{width:100vw}.min-w-0{min-width:0}.min-w-32{min-width:8rem}.min-w-40{min-width:10rem}.min-w-\\[1024px\\]{min-width:1024px}.min-w-\\[300px\\]{min-width:300px}.min-w-\\[42rem\\]{min-width:42rem}.min-w-\\[46rem\\]{min-width:46rem}.min-w-max{min-width:max-content}.max-w-28{max-width:7rem}.max-w-2xl{max-width:42rem}.max-w-3xl{max-width:48rem}.max-w-4xl{max-width:56rem}.max-w-56{max-width:14rem}.max-w-\\[110rem\\]{max-width:110rem}.max-w-\\[150px\\]{max-width:150px}.max-w-\\[160px\\]{max-width:160px}.max-w-\\[180px\\]{max-width:180px}.max-w-\\[85\\%\\]{max-width:85%}.max-w-\\[90\\%\\]{max-width:90%}.max-w-\\[calc\\(100vw-1rem\\)\\]{max-width:calc(100vw - 1rem)}.flex-1{flex:1}.flex-shrink-0,.shrink-0{flex-shrink:0}.table-fixed{table-layout:fixed}.-translate-x-1\\/2{--tw-translate-x:-50%;transform:translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y))}.rotate-45{--tw-rotate:45deg;transform:translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y))}.transform{transform:translate(var(--tw-translate-x), var(--tw-translate-y)) rotate(var(--tw-rotate)) skewX(var(--tw-skew-x)) skewY(var(--tw-skew-y)) scaleX(var(--tw-scale-x)) scaleY(var(--tw-scale-y))}@keyframes ping{75%,to{opacity:0;transform:scale(2)}}.animate-ping{animation:1s cubic-bezier(0,0,.2,1) infinite ping}@keyframes pulse{50%{opacity:.5}}.animate-pulse{animation:2s cubic-bezier(.4,0,.6,1) infinite pulse}@keyframes spin{to{transform:rotate(360deg)}}.animate-spin{animation:1s linear infinite spin}.cursor-default{cursor:default}.cursor-grab{cursor:grab}.cursor-pointer{cursor:pointer}.cursor-row-resize{cursor:row-resize}.select-none{-webkit-user-select:none;user-select:none}.resize-none{resize:none}.resize-y{resize:vertical}.resize{resize:both}.list-disc{list-style-type:disc}.grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}.grid-cols-3{grid-template-columns:repeat(3,minmax(0,1fr))}.grid-cols-4{grid-template-columns:repeat(4,minmax(0,1fr))}.grid-cols-\\[10\\.5rem_minmax\\(32rem\\,1fr\\)\\]{grid-template-columns:10.5rem minmax(32rem,1fr)}.grid-cols-\\[100px_1fr\\]{grid-template-columns:100px 1fr}.grid-cols-\\[1fr_1\\.5fr\\]{grid-template-columns:1fr 1.5fr}.grid-cols-\\[auto_1fr\\]{grid-template-columns:auto 1fr}.grid-cols-\\[minmax\\(0\\,1fr\\)_14rem\\]{grid-template-columns:minmax(0,1fr) 14rem}.grid-cols-\\[minmax\\(0\\,1fr\\)_minmax\\(0\\,1fr\\)\\]{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}.grid-cols-\\[minmax\\(0\\,2fr\\)_minmax\\(0\\,3fr\\)\\]{grid-template-columns:minmax(0,2fr) minmax(0,3fr)}.grid-cols-\\[minmax\\(13rem\\,16\\.25rem\\)_minmax\\(0\\,1fr\\)\\]{grid-template-columns:minmax(13rem,16.25rem) minmax(0,1fr)}.flex-col{flex-direction:column}.flex-wrap{flex-wrap:wrap}.items-start{align-items:flex-start}.items-end{align-items:flex-end}.items-center{align-items:center}.items-stretch{align-items:stretch}.justify-end{justify-content:flex-end}.justify-center{justify-content:center}.justify-between{justify-content:space-between}.gap-1{gap:.25rem}.gap-1\\.5{gap:.375rem}.gap-2{gap:.5rem}.gap-3{gap:.75rem}.gap-4{gap:1rem}.gap-x-2{-moz-column-gap:.5rem;column-gap:.5rem}.gap-x-3{-moz-column-gap:.75rem;column-gap:.75rem}.gap-x-4{-moz-column-gap:1rem;column-gap:1rem}.gap-x-6{-moz-column-gap:1.5rem;column-gap:1.5rem}.gap-y-1{row-gap:.25rem}.space-y-0\\.5>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(.125rem * calc(1 - var(--tw-space-y-reverse)));margin-bottom:calc(.125rem * var(--tw-space-y-reverse))}.space-y-1>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(.25rem * calc(1 - var(--tw-space-y-reverse)));margin-bottom:calc(.25rem * var(--tw-space-y-reverse))}.space-y-1\\.5>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(.375rem * calc(1 - var(--tw-space-y-reverse)));margin-bottom:calc(.375rem * var(--tw-space-y-reverse))}.space-y-2>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(.5rem * calc(1 - var(--tw-space-y-reverse)));margin-bottom:calc(.5rem * var(--tw-space-y-reverse))}.space-y-3>:not([hidden])~:not([hidden]){--tw-space-y-reverse:0;margin-top:calc(.75rem * calc(1 - var(--tw-space-y-reverse)));margin-bottom:calc(.75rem * var(--tw-space-y-reverse))}.overflow-auto{overflow:auto}.overflow-hidden{overflow:hidden}.overflow-x-auto{overflow-x:auto}.overflow-y-auto{overflow-y:auto}.truncate{text-overflow:ellipsis;white-space:nowrap;overflow:hidden}.whitespace-normal{white-space:normal}.whitespace-nowrap{white-space:nowrap}.whitespace-pre-wrap{white-space:pre-wrap}.break-words{overflow-wrap:break-word}.break-all{word-break:break-all}.rounded{border-radius:.25rem}.rounded-2xl{border-radius:1rem}.rounded-full{border-radius:9999px}.rounded-lg{border-radius:.5rem}.rounded-xl{border-radius:.75rem}.rounded-t{border-top-left-radius:.25rem;border-top-right-radius:.25rem}.rounded-t-lg{border-top-left-radius:.5rem;border-top-right-radius:.5rem}.rounded-t-md{border-top-left-radius:.375rem;border-top-right-radius:.375rem}.border{border-width:1px}.border-2{border-width:2px}.border-x{border-left-width:1px;border-right-width:1px}.border-b{border-bottom-width:1px}.border-b-2{border-bottom-width:2px}.border-l{border-left-width:1px}.border-l-2{border-left-width:2px}.border-r{border-right-width:1px}.border-t{border-top-width:1px}.border-solid{border-style:solid}.border-dashed{border-style:dashed}.\\!border-gray-700{--tw-border-opacity:1!important;border-color:rgb(55 65 81/var(--tw-border-opacity,1))!important}.border-amber-300{--tw-border-opacity:1;border-color:rgb(252 211 77/var(--tw-border-opacity,1))}.border-amber-500{--tw-border-opacity:1;border-color:rgb(245 158 11/var(--tw-border-opacity,1))}.border-amber-500\\/80{border-color:#f59e0bcc}.border-amber-600{--tw-border-opacity:1;border-color:rgb(217 119 6/var(--tw-border-opacity,1))}.border-amber-700{--tw-border-opacity:1;border-color:rgb(180 83 9/var(--tw-border-opacity,1))}.border-amber-800{--tw-border-opacity:1;border-color:rgb(146 64 14/var(--tw-border-opacity,1))}.border-amber-900{--tw-border-opacity:1;border-color:rgb(120 53 15/var(--tw-border-opacity,1))}.border-amber-900\\/80{border-color:#78350fcc}.border-amber-950\\/80{border-color:#451a03cc}.border-blue-300{--tw-border-opacity:1;border-color:rgb(147 197 253/var(--tw-border-opacity,1))}.border-blue-500{--tw-border-opacity:1;border-color:rgb(59 130 246/var(--tw-border-opacity,1))}.border-blue-700{--tw-border-opacity:1;border-color:rgb(29 78 216/var(--tw-border-opacity,1))}.border-blue-800{--tw-border-opacity:1;border-color:rgb(30 64 175/var(--tw-border-opacity,1))}.border-current{border-color:currentColor}.border-cyan-300{--tw-border-opacity:1;border-color:rgb(103 232 249/var(--tw-border-opacity,1))}.border-cyan-300\\/30{border-color:#67e8f94d}.border-cyan-600{--tw-border-opacity:1;border-color:rgb(8 145 178/var(--tw-border-opacity,1))}.border-cyan-700{--tw-border-opacity:1;border-color:rgb(14 116 144/var(--tw-border-opacity,1))}.border-cyan-800{--tw-border-opacity:1;border-color:rgb(21 94 117/var(--tw-border-opacity,1))}.border-cyan-900{--tw-border-opacity:1;border-color:rgb(22 78 99/var(--tw-border-opacity,1))}.border-cyan-950{--tw-border-opacity:1;border-color:rgb(8 51 68/var(--tw-border-opacity,1))}.border-emerald-400{--tw-border-opacity:1;border-color:rgb(52 211 153/var(--tw-border-opacity,1))}.border-emerald-800{--tw-border-opacity:1;border-color:rgb(6 95 70/var(--tw-border-opacity,1))}.border-emerald-900{--tw-border-opacity:1;border-color:rgb(6 78 59/var(--tw-border-opacity,1))}.border-gray-500{--tw-border-opacity:1;border-color:rgb(107 114 128/var(--tw-border-opacity,1))}.border-gray-600{--tw-border-opacity:1;border-color:rgb(75 85 99/var(--tw-border-opacity,1))}.border-gray-700{--tw-border-opacity:1;border-color:rgb(55 65 81/var(--tw-border-opacity,1))}.border-gray-700\\/50{border-color:#37415180}.border-gray-800{--tw-border-opacity:1;border-color:rgb(31 41 55/var(--tw-border-opacity,1))}.border-green-500{--tw-border-opacity:1;border-color:rgb(34 197 94/var(--tw-border-opacity,1))}.border-indigo-700{--tw-border-opacity:1;border-color:rgb(67 56 202/var(--tw-border-opacity,1))}.border-indigo-800{--tw-border-opacity:1;border-color:rgb(55 48 163/var(--tw-border-opacity,1))}.border-orange-700{--tw-border-opacity:1;border-color:rgb(194 65 12/var(--tw-border-opacity,1))}.border-purple-500{--tw-border-opacity:1;border-color:rgb(168 85 247/var(--tw-border-opacity,1))}.border-purple-800\\/50{border-color:#6b21a880}.border-red-500{--tw-border-opacity:1;border-color:rgb(239 68 68/var(--tw-border-opacity,1))}.border-red-700{--tw-border-opacity:1;border-color:rgb(185 28 28/var(--tw-border-opacity,1))}.border-red-800{--tw-border-opacity:1;border-color:rgb(153 27 27/var(--tw-border-opacity,1))}.border-red-900{--tw-border-opacity:1;border-color:rgb(127 29 29/var(--tw-border-opacity,1))}.border-sky-800{--tw-border-opacity:1;border-color:rgb(7 89 133/var(--tw-border-opacity,1))}.border-sky-900{--tw-border-opacity:1;border-color:rgb(12 74 110/var(--tw-border-opacity,1))}.border-slate-500{--tw-border-opacity:1;border-color:rgb(100 116 139/var(--tw-border-opacity,1))}.border-slate-600{--tw-border-opacity:1;border-color:rgb(71 85 105/var(--tw-border-opacity,1))}.border-slate-700{--tw-border-opacity:1;border-color:rgb(51 65 85/var(--tw-border-opacity,1))}.border-slate-700\\/70{border-color:#334155b3}.border-slate-800{--tw-border-opacity:1;border-color:rgb(30 41 59/var(--tw-border-opacity,1))}.border-slate-900{--tw-border-opacity:1;border-color:rgb(15 23 42/var(--tw-border-opacity,1))}.border-transparent{border-color:#0000}.border-violet-300{--tw-border-opacity:1;border-color:rgb(196 181 253/var(--tw-border-opacity,1))}.border-violet-700{--tw-border-opacity:1;border-color:rgb(109 40 217/var(--tw-border-opacity,1))}.border-violet-800{--tw-border-opacity:1;border-color:rgb(91 33 182/var(--tw-border-opacity,1))}.border-violet-900{--tw-border-opacity:1;border-color:rgb(76 29 149/var(--tw-border-opacity,1))}.border-yellow-500{--tw-border-opacity:1;border-color:rgb(234 179 8/var(--tw-border-opacity,1))}.border-yellow-500\\/80{border-color:#eab308cc}.border-t-cyan-300{--tw-border-opacity:1;border-top-color:rgb(103 232 249/var(--tw-border-opacity,1))}.border-t-transparent{border-top-color:#0000}.\\!bg-gray-800{--tw-bg-opacity:1!important;background-color:rgb(31 41 55/var(--tw-bg-opacity,1))!important}.bg-\\[\\#1e293b\\]{--tw-bg-opacity:1;background-color:rgb(30 41 59/var(--tw-bg-opacity,1))}.bg-amber-400{--tw-bg-opacity:1;background-color:rgb(251 191 36/var(--tw-bg-opacity,1))}.bg-amber-500{--tw-bg-opacity:1;background-color:rgb(245 158 11/var(--tw-bg-opacity,1))}.bg-amber-500\\/85{background-color:#f59e0bd9}.bg-amber-600{--tw-bg-opacity:1;background-color:rgb(217 119 6/var(--tw-bg-opacity,1))}.bg-amber-700{--tw-bg-opacity:1;background-color:rgb(180 83 9/var(--tw-bg-opacity,1))}.bg-amber-900{--tw-bg-opacity:1;background-color:rgb(120 53 15/var(--tw-bg-opacity,1))}.bg-amber-900\\/40{background-color:#78350f66}.bg-amber-950{--tw-bg-opacity:1;background-color:rgb(69 26 3/var(--tw-bg-opacity,1))}.bg-amber-950\\/30{background-color:#451a034d}.bg-amber-950\\/40{background-color:#451a0366}.bg-amber-950\\/50{background-color:#451a0380}.bg-amber-950\\/60{background-color:#451a0399}.bg-amber-950\\/70{background-color:#451a03b3}.bg-amber-950\\/80{background-color:#451a03cc}.bg-black{--tw-bg-opacity:1;background-color:rgb(0 0 0/var(--tw-bg-opacity,1))}.bg-black\\/20{background-color:#0003}.bg-black\\/25{background-color:#00000040}.bg-black\\/30{background-color:#0000004d}.bg-black\\/70{background-color:#000000b3}.bg-blue-500{--tw-bg-opacity:1;background-color:rgb(59 130 246/var(--tw-bg-opacity,1))}.bg-blue-600{--tw-bg-opacity:1;background-color:rgb(37 99 235/var(--tw-bg-opacity,1))}.bg-blue-700{--tw-bg-opacity:1;background-color:rgb(29 78 216/var(--tw-bg-opacity,1))}.bg-blue-900{--tw-bg-opacity:1;background-color:rgb(30 58 138/var(--tw-bg-opacity,1))}.bg-blue-950{--tw-bg-opacity:1;background-color:rgb(23 37 84/var(--tw-bg-opacity,1))}.bg-current{background-color:currentColor}.bg-cyan-400{--tw-bg-opacity:1;background-color:rgb(34 211 238/var(--tw-bg-opacity,1))}.bg-cyan-700{--tw-bg-opacity:1;background-color:rgb(14 116 144/var(--tw-bg-opacity,1))}.bg-cyan-700\\/45{background-color:#0e749073}.bg-cyan-800{--tw-bg-opacity:1;background-color:rgb(21 94 117/var(--tw-bg-opacity,1))}.bg-cyan-950{--tw-bg-opacity:1;background-color:rgb(8 51 68/var(--tw-bg-opacity,1))}.bg-cyan-950\\/20{background-color:#08334433}.bg-cyan-950\\/30{background-color:#0833444d}.bg-cyan-950\\/40{background-color:#08334466}.bg-cyan-950\\/50{background-color:#08334480}.bg-cyan-950\\/60{background-color:#08334499}.bg-emerald-500{--tw-bg-opacity:1;background-color:rgb(16 185 129/var(--tw-bg-opacity,1))}.bg-emerald-600\\/80{background-color:#059669cc}.bg-emerald-700{--tw-bg-opacity:1;background-color:rgb(4 120 87/var(--tw-bg-opacity,1))}.bg-emerald-900{--tw-bg-opacity:1;background-color:rgb(6 78 59/var(--tw-bg-opacity,1))}.bg-emerald-950{--tw-bg-opacity:1;background-color:rgb(2 44 34/var(--tw-bg-opacity,1))}.bg-emerald-950\\/20{background-color:#022c2233}.bg-emerald-950\\/40{background-color:#022c2266}.bg-gray-700{--tw-bg-opacity:1;background-color:rgb(55 65 81/var(--tw-bg-opacity,1))}.bg-gray-800{--tw-bg-opacity:1;background-color:rgb(31 41 55/var(--tw-bg-opacity,1))}.bg-gray-800\\/50{background-color:#1f293780}.bg-gray-900{--tw-bg-opacity:1;background-color:rgb(17 24 39/var(--tw-bg-opacity,1))}.bg-gray-900\\/50{background-color:#11182780}.bg-green-500{--tw-bg-opacity:1;background-color:rgb(34 197 94/var(--tw-bg-opacity,1))}.bg-green-800{--tw-bg-opacity:1;background-color:rgb(22 101 52/var(--tw-bg-opacity,1))}.bg-green-900{--tw-bg-opacity:1;background-color:rgb(20 83 45/var(--tw-bg-opacity,1))}.bg-indigo-900{--tw-bg-opacity:1;background-color:rgb(49 46 129/var(--tw-bg-opacity,1))}.bg-indigo-950\\/30{background-color:#1e1b4b4d}.bg-orange-800{--tw-bg-opacity:1;background-color:rgb(154 52 18/var(--tw-bg-opacity,1))}.bg-orange-900{--tw-bg-opacity:1;background-color:rgb(124 45 18/var(--tw-bg-opacity,1))}.bg-orange-950{--tw-bg-opacity:1;background-color:rgb(67 20 7/var(--tw-bg-opacity,1))}.bg-orange-950\\/30{background-color:#4314074d}.bg-purple-600{--tw-bg-opacity:1;background-color:rgb(147 51 234/var(--tw-bg-opacity,1))}.bg-purple-800{--tw-bg-opacity:1;background-color:rgb(107 33 168/var(--tw-bg-opacity,1))}.bg-purple-900{--tw-bg-opacity:1;background-color:rgb(88 28 135/var(--tw-bg-opacity,1))}.bg-purple-900\\/50{background-color:#581c8780}.bg-purple-950{--tw-bg-opacity:1;background-color:rgb(59 7 100/var(--tw-bg-opacity,1))}.bg-purple-950\\/30{background-color:#3b07644d}.bg-red-600{--tw-bg-opacity:1;background-color:rgb(220 38 38/var(--tw-bg-opacity,1))}.bg-red-700{--tw-bg-opacity:1;background-color:rgb(185 28 28/var(--tw-bg-opacity,1))}.bg-red-800{--tw-bg-opacity:1;background-color:rgb(153 27 27/var(--tw-bg-opacity,1))}.bg-red-900{--tw-bg-opacity:1;background-color:rgb(127 29 29/var(--tw-bg-opacity,1))}.bg-red-900\\/30{background-color:#7f1d1d4d}.bg-red-950{--tw-bg-opacity:1;background-color:rgb(69 10 10/var(--tw-bg-opacity,1))}.bg-red-950\\/30{background-color:#450a0a4d}.bg-red-950\\/40{background-color:#450a0a66}.bg-red-950\\/50{background-color:#450a0a80}.bg-red-950\\/60{background-color:#450a0a99}.bg-red-950\\/70{background-color:#450a0ab3}.bg-red-950\\/80{background-color:#450a0acc}.bg-sky-800{--tw-bg-opacity:1;background-color:rgb(7 89 133/var(--tw-bg-opacity,1))}.bg-sky-900{--tw-bg-opacity:1;background-color:rgb(12 74 110/var(--tw-bg-opacity,1))}.bg-sky-950{--tw-bg-opacity:1;background-color:rgb(8 47 73/var(--tw-bg-opacity,1))}.bg-sky-950\\/30{background-color:#082f494d}.bg-slate-500{--tw-bg-opacity:1;background-color:rgb(100 116 139/var(--tw-bg-opacity,1))}.bg-slate-600\\/70{background-color:#475569b3}.bg-slate-700{--tw-bg-opacity:1;background-color:rgb(51 65 85/var(--tw-bg-opacity,1))}.bg-slate-800{--tw-bg-opacity:1;background-color:rgb(30 41 59/var(--tw-bg-opacity,1))}.bg-slate-900{--tw-bg-opacity:1;background-color:rgb(15 23 42/var(--tw-bg-opacity,1))}.bg-slate-900\\/60{background-color:#0f172a99}.bg-slate-950{--tw-bg-opacity:1;background-color:rgb(2 6 23/var(--tw-bg-opacity,1))}.bg-slate-950\\/90{background-color:#020617e6}.bg-slate-950\\/95{background-color:#020617f2}.bg-violet-500{--tw-bg-opacity:1;background-color:rgb(139 92 246/var(--tw-bg-opacity,1))}.bg-violet-700{--tw-bg-opacity:1;background-color:rgb(109 40 217/var(--tw-bg-opacity,1))}.bg-violet-950{--tw-bg-opacity:1;background-color:rgb(46 16 101/var(--tw-bg-opacity,1))}.bg-violet-950\\/20{background-color:#2e106533}.bg-violet-950\\/30{background-color:#2e10654d}.bg-violet-950\\/40{background-color:#2e106566}.bg-yellow-500{--tw-bg-opacity:1;background-color:rgb(234 179 8/var(--tw-bg-opacity,1))}.bg-yellow-800{--tw-bg-opacity:1;background-color:rgb(133 77 14/var(--tw-bg-opacity,1))}.bg-yellow-900{--tw-bg-opacity:1;background-color:rgb(113 63 18/var(--tw-bg-opacity,1))}.bg-yellow-950\\/50{background-color:#42200680}.p-0\\.5{padding:.125rem}.p-1{padding:.25rem}.p-1\\.5{padding:.375rem}.p-2{padding:.5rem}.p-3{padding:.75rem}.p-4{padding:1rem}.p-5{padding:1.25rem}.p-6{padding:1.5rem}.p-8{padding:2rem}.px-0{padding-left:0;padding-right:0}.px-1{padding-left:.25rem;padding-right:.25rem}.px-1\\.5{padding-left:.375rem;padding-right:.375rem}.px-2{padding-left:.5rem;padding-right:.5rem}.px-3{padding-left:.75rem;padding-right:.75rem}.px-4{padding-left:1rem;padding-right:1rem}.px-8{padding-left:2rem;padding-right:2rem}.py-0\\.5{padding-top:.125rem;padding-bottom:.125rem}.py-1{padding-top:.25rem;padding-bottom:.25rem}.py-1\\.5{padding-top:.375rem;padding-bottom:.375rem}.py-2{padding-top:.5rem;padding-bottom:.5rem}.py-3{padding-top:.75rem;padding-bottom:.75rem}.py-4{padding-top:1rem;padding-bottom:1rem}.py-8{padding-top:2rem;padding-bottom:2rem}.pb-1{padding-bottom:.25rem}.pb-2{padding-bottom:.5rem}.pl-2{padding-left:.5rem}.pl-4{padding-left:1rem}.pr-2{padding-right:.5rem}.pt-1{padding-top:.25rem}.pt-1\\.5{padding-top:.375rem}.pt-2{padding-top:.5rem}.pt-3{padding-top:.75rem}.text-left{text-align:left}.text-center{text-align:center}.text-right{text-align:right}.font-mono{font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,Liberation Mono,Courier New,monospace}.font-sans{font-family:ui-sans-serif,system-ui,sans-serif,Apple Color Emoji,Segoe UI Emoji,Segoe UI Symbol,Noto Color Emoji}.text-2xl{font-size:1.5rem;line-height:2rem}.text-\\[10px\\]{font-size:10px}.text-\\[11px\\]{font-size:11px}.text-\\[9px\\]{font-size:9px}.text-base{font-size:1rem;line-height:1.5rem}.text-lg{font-size:1.125rem;line-height:1.75rem}.text-sm{font-size:.875rem;line-height:1.25rem}.text-xs{font-size:.75rem;line-height:1rem}.font-bold{font-weight:700}.font-medium{font-weight:500}.font-normal{font-weight:400}.font-semibold{font-weight:600}.uppercase{text-transform:uppercase}.lowercase{text-transform:lowercase}.normal-case{text-transform:none}.italic{font-style:italic}.leading-none{line-height:1}.leading-relaxed{line-height:1.625}.leading-tight{line-height:1.25}.tracking-normal{letter-spacing:0}.tracking-wide{letter-spacing:.025em}.text-amber-100{--tw-text-opacity:1;color:rgb(254 243 199/var(--tw-text-opacity,1))}.text-amber-200{--tw-text-opacity:1;color:rgb(253 230 138/var(--tw-text-opacity,1))}.text-amber-200\\/70{color:#fde68ab3}.text-amber-200\\/80{color:#fde68acc}.text-amber-300{--tw-text-opacity:1;color:rgb(252 211 77/var(--tw-text-opacity,1))}.text-amber-300\\/70{color:#fcd34db3}.text-amber-300\\/80{color:#fcd34dcc}.text-amber-400{--tw-text-opacity:1;color:rgb(251 191 36/var(--tw-text-opacity,1))}.text-amber-50{--tw-text-opacity:1;color:rgb(255 251 235/var(--tw-text-opacity,1))}.text-blue-100{--tw-text-opacity:1;color:rgb(219 234 254/var(--tw-text-opacity,1))}.text-blue-200{--tw-text-opacity:1;color:rgb(191 219 254/var(--tw-text-opacity,1))}.text-blue-300{--tw-text-opacity:1;color:rgb(147 197 253/var(--tw-text-opacity,1))}.text-blue-400{--tw-text-opacity:1;color:rgb(96 165 250/var(--tw-text-opacity,1))}.text-cyan-100{--tw-text-opacity:1;color:rgb(207 250 254/var(--tw-text-opacity,1))}.text-cyan-200{--tw-text-opacity:1;color:rgb(165 243 252/var(--tw-text-opacity,1))}.text-cyan-300{--tw-text-opacity:1;color:rgb(103 232 249/var(--tw-text-opacity,1))}.text-cyan-400{--tw-text-opacity:1;color:rgb(34 211 238/var(--tw-text-opacity,1))}.text-cyan-50{--tw-text-opacity:1;color:rgb(236 254 255/var(--tw-text-opacity,1))}.text-cyan-500{--tw-text-opacity:1;color:rgb(6 182 212/var(--tw-text-opacity,1))}.text-cyan-700{--tw-text-opacity:1;color:rgb(14 116 144/var(--tw-text-opacity,1))}.text-emerald-200{--tw-text-opacity:1;color:rgb(167 243 208/var(--tw-text-opacity,1))}.text-emerald-300{--tw-text-opacity:1;color:rgb(110 231 183/var(--tw-text-opacity,1))}.text-emerald-400{--tw-text-opacity:1;color:rgb(52 211 153/var(--tw-text-opacity,1))}.text-emerald-500{--tw-text-opacity:1;color:rgb(16 185 129/var(--tw-text-opacity,1))}.text-gray-100{--tw-text-opacity:1;color:rgb(243 244 246/var(--tw-text-opacity,1))}.text-gray-200{--tw-text-opacity:1;color:rgb(229 231 235/var(--tw-text-opacity,1))}.text-gray-300{--tw-text-opacity:1;color:rgb(209 213 219/var(--tw-text-opacity,1))}.text-gray-400{--tw-text-opacity:1;color:rgb(156 163 175/var(--tw-text-opacity,1))}.text-gray-500{--tw-text-opacity:1;color:rgb(107 114 128/var(--tw-text-opacity,1))}.text-gray-600{--tw-text-opacity:1;color:rgb(75 85 99/var(--tw-text-opacity,1))}.text-gray-700{--tw-text-opacity:1;color:rgb(55 65 81/var(--tw-text-opacity,1))}.text-green-100{--tw-text-opacity:1;color:rgb(220 252 231/var(--tw-text-opacity,1))}.text-green-200{--tw-text-opacity:1;color:rgb(187 247 208/var(--tw-text-opacity,1))}.text-green-300{--tw-text-opacity:1;color:rgb(134 239 172/var(--tw-text-opacity,1))}.text-green-400{--tw-text-opacity:1;color:rgb(74 222 128/var(--tw-text-opacity,1))}.text-indigo-100{--tw-text-opacity:1;color:rgb(224 231 255/var(--tw-text-opacity,1))}.text-indigo-100\\/90{color:#e0e7ffe6}.text-indigo-200{--tw-text-opacity:1;color:rgb(199 210 254/var(--tw-text-opacity,1))}.text-indigo-200\\/70{color:#c7d2feb3}.text-indigo-300{--tw-text-opacity:1;color:rgb(165 180 252/var(--tw-text-opacity,1))}.text-orange-100{--tw-text-opacity:1;color:rgb(255 237 213/var(--tw-text-opacity,1))}.text-orange-200{--tw-text-opacity:1;color:rgb(254 215 170/var(--tw-text-opacity,1))}.text-orange-300{--tw-text-opacity:1;color:rgb(253 186 116/var(--tw-text-opacity,1))}.text-orange-400{--tw-text-opacity:1;color:rgb(251 146 60/var(--tw-text-opacity,1))}.text-purple-100{--tw-text-opacity:1;color:rgb(243 232 255/var(--tw-text-opacity,1))}.text-purple-200{--tw-text-opacity:1;color:rgb(233 213 255/var(--tw-text-opacity,1))}.text-purple-300{--tw-text-opacity:1;color:rgb(216 180 254/var(--tw-text-opacity,1))}.text-purple-400{--tw-text-opacity:1;color:rgb(192 132 252/var(--tw-text-opacity,1))}.text-red-100{--tw-text-opacity:1;color:rgb(254 226 226/var(--tw-text-opacity,1))}.text-red-200{--tw-text-opacity:1;color:rgb(254 202 202/var(--tw-text-opacity,1))}.text-red-200\\/80{color:#fecacacc}.text-red-300{--tw-text-opacity:1;color:rgb(252 165 165/var(--tw-text-opacity,1))}.text-red-300\\/70{color:#fca5a5b3}.text-red-400{--tw-text-opacity:1;color:rgb(248 113 113/var(--tw-text-opacity,1))}.text-sky-100{--tw-text-opacity:1;color:rgb(224 242 254/var(--tw-text-opacity,1))}.text-sky-200{--tw-text-opacity:1;color:rgb(186 230 253/var(--tw-text-opacity,1))}.text-sky-200\\/80{color:#bae6fdcc}.text-sky-300{--tw-text-opacity:1;color:rgb(125 211 252/var(--tw-text-opacity,1))}.text-sky-400{--tw-text-opacity:1;color:rgb(56 189 248/var(--tw-text-opacity,1))}.text-sky-400\\/70{color:#38bdf8b3}.text-slate-100{--tw-text-opacity:1;color:rgb(241 245 249/var(--tw-text-opacity,1))}.text-slate-200{--tw-text-opacity:1;color:rgb(226 232 240/var(--tw-text-opacity,1))}.text-slate-300{--tw-text-opacity:1;color:rgb(203 213 225/var(--tw-text-opacity,1))}.text-slate-400{--tw-text-opacity:1;color:rgb(148 163 184/var(--tw-text-opacity,1))}.text-slate-500{--tw-text-opacity:1;color:rgb(100 116 139/var(--tw-text-opacity,1))}.text-slate-600{--tw-text-opacity:1;color:rgb(71 85 105/var(--tw-text-opacity,1))}.text-slate-950{--tw-text-opacity:1;color:rgb(2 6 23/var(--tw-text-opacity,1))}.text-violet-100{--tw-text-opacity:1;color:rgb(237 233 254/var(--tw-text-opacity,1))}.text-violet-200{--tw-text-opacity:1;color:rgb(221 214 254/var(--tw-text-opacity,1))}.text-violet-300{--tw-text-opacity:1;color:rgb(196 181 253/var(--tw-text-opacity,1))}.text-white{--tw-text-opacity:1;color:rgb(255 255 255/var(--tw-text-opacity,1))}.text-yellow-100{--tw-text-opacity:1;color:rgb(254 249 195/var(--tw-text-opacity,1))}.text-yellow-200{--tw-text-opacity:1;color:rgb(254 240 138/var(--tw-text-opacity,1))}.text-yellow-300{--tw-text-opacity:1;color:rgb(253 224 71/var(--tw-text-opacity,1))}.underline{text-decoration-line:underline}.line-through{text-decoration-line:line-through}.placeholder-gray-600::placeholder{--tw-placeholder-opacity:1;color:rgb(75 85 99/var(--tw-placeholder-opacity,1))}.placeholder-gray-700::placeholder{--tw-placeholder-opacity:1;color:rgb(55 65 81/var(--tw-placeholder-opacity,1))}.opacity-100{opacity:1}.opacity-50{opacity:.5}.opacity-60{opacity:.6}.opacity-70{opacity:.7}.opacity-75{opacity:.75}.shadow{--tw-shadow:0 1px 3px 0 #0000001a, 0 1px 2px -1px #0000001a;--tw-shadow-colored:0 1px 3px 0 var(--tw-shadow-color), 0 1px 2px -1px var(--tw-shadow-color);box-shadow:var(--tw-ring-offset-shadow,0 0 #0000), var(--tw-ring-shadow,0 0 #0000), var(--tw-shadow)}.shadow-2xl{--tw-shadow:0 25px 50px -12px #00000040;--tw-shadow-colored:0 25px 50px -12px var(--tw-shadow-color);box-shadow:var(--tw-ring-offset-shadow,0 0 #0000), var(--tw-ring-shadow,0 0 #0000), var(--tw-shadow)}.shadow-lg{--tw-shadow:0 10px 15px -3px #0000001a, 0 4px 6px -4px #0000001a;--tw-shadow-colored:0 10px 15px -3px var(--tw-shadow-color), 0 4px 6px -4px var(--tw-shadow-color);box-shadow:var(--tw-ring-offset-shadow,0 0 #0000), var(--tw-ring-shadow,0 0 #0000), var(--tw-shadow)}.shadow-xl{--tw-shadow:0 20px 25px -5px #0000001a, 0 8px 10px -6px #0000001a;--tw-shadow-colored:0 20px 25px -5px var(--tw-shadow-color), 0 8px 10px -6px var(--tw-shadow-color);box-shadow:var(--tw-ring-offset-shadow,0 0 #0000), var(--tw-ring-shadow,0 0 #0000), var(--tw-shadow)}.shadow-amber-950\\/30{--tw-shadow-color:#451a034d;--tw-shadow:var(--tw-shadow-colored)}.shadow-amber-950\\/40{--tw-shadow-color:#451a0366;--tw-shadow:var(--tw-shadow-colored)}.shadow-yellow-950\\/40{--tw-shadow-color:#42200666;--tw-shadow:var(--tw-shadow-colored)}.shadow-yellow-950\\/50{--tw-shadow-color:#42200680;--tw-shadow:var(--tw-shadow-colored)}.outline{outline-style:solid}.ring-1{--tw-ring-offset-shadow:var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);--tw-ring-shadow:var(--tw-ring-inset) 0 0 0 calc(1px + var(--tw-ring-offset-width)) var(--tw-ring-color);box-shadow:var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow,0 0 #0000)}.ring-2{--tw-ring-offset-shadow:var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);--tw-ring-shadow:var(--tw-ring-inset) 0 0 0 calc(2px + var(--tw-ring-offset-width)) var(--tw-ring-color);box-shadow:var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow,0 0 #0000)}.ring-slate-800{--tw-ring-opacity:1;--tw-ring-color:rgb(30 41 59/var(--tw-ring-opacity,1))}.ring-yellow-400\\/90{--tw-ring-color:#facc15e6}.blur{--tw-blur:blur(8px);filter:var(--tw-blur) var(--tw-brightness) var(--tw-contrast) var(--tw-grayscale) var(--tw-hue-rotate) var(--tw-invert) var(--tw-saturate) var(--tw-sepia) var(--tw-drop-shadow)}.grayscale{--tw-grayscale:grayscale(100%);filter:var(--tw-blur) var(--tw-brightness) var(--tw-contrast) var(--tw-grayscale) var(--tw-hue-rotate) var(--tw-invert) var(--tw-saturate) var(--tw-sepia) var(--tw-drop-shadow)}.filter{filter:var(--tw-blur) var(--tw-brightness) var(--tw-contrast) var(--tw-grayscale) var(--tw-hue-rotate) var(--tw-invert) var(--tw-saturate) var(--tw-sepia) var(--tw-drop-shadow)}.transition-all{transition-property:all;transition-duration:.15s;transition-timing-function:cubic-bezier(.4,0,.2,1)}.duration-500{transition-duration:.5s}.react-flow__node-input,.react-flow__node-output,.react-flow__node-tool,.react-flow__node-llm{box-shadow:none!important;background:0 0!important;border:0!important}.react-flow__node.selected>div{box-shadow:0 0 0 2px #60a5faa6}.react-flow__node.verso-run-node-completed>div{box-shadow:0 0 0 2px #34d3998c}.react-flow__node.verso-run-node-running>div{box-shadow:0 0 0 3px #fbbf24b3,0 0 20px #f59e0b40}.react-flow__node.verso-run-node-failed>div,.react-flow__node.verso-run-node-blocked>div{box-shadow:0 0 0 3px #f87171bf,0 0 18px #ef444438}.react-flow__node.verso-run-node-queued>div,.react-flow__node.verso-run-node-waiting>div{box-shadow:0 0 0 2px #60a5fa73}.react-flow__node.verso-run-node-diagnostic-warning>div{outline-offset:4px;outline:2px dashed #fbbf24bf}.react-flow__node.verso-run-node-diagnostic-error>div{outline-offset:4px;outline:3px double #f87171e6}.react-flow__edge.verso-run-edge .react-flow__edge-path{stroke-width:2.5px}.react-flow__edge.verso-run-edge-completed .react-flow__edge-path{stroke:#34d399cc}.react-flow__edge.verso-run-edge-running .react-flow__edge-path{filter:drop-shadow(0 0 4px #fbbf24a6);stroke:#fbbf24;stroke-width:3.5px}.react-flow__edge.verso-run-edge-queued .react-flow__edge-path{stroke:#60a5fab3;stroke-dasharray:7 6}.react-flow__edge.verso-run-edge-failed .react-flow__edge-path{stroke:#f87171d9}.react-flow__edge.verso-run-edge-skipped .react-flow__edge-path{stroke:#64748b8c;stroke-dasharray:4 7}.react-flow__node.verso-agent-highlight-soft>div{transition:box-shadow .22s ease-out;box-shadow:0 0 0 2px #facc158c,0 0 12px #facc1538}.react-flow__node.verso-agent-highlight>div{animation:1.2s ease-in-out infinite alternate verso-agent-highlight-pulse;box-shadow:0 0 0 3px #facc15e6,0 0 24px #facc15a6}@keyframes verso-agent-highlight-pulse{0%{box-shadow:0 0 0 3px #facc15bf,0 0 14px #facc1573}to{box-shadow:0 0 0 4px #facc15,0 0 30px #facc15bf}}.react-flow__edge.verso-agent-edge-highlight .react-flow__edge-path{filter:drop-shadow(0 0 5px #facc15cc);stroke-dasharray:10 7;animation:.9s linear infinite verso-agent-edge-flow;stroke:#facc15!important;stroke-width:4px!important}.react-flow__edge.verso-agent-edge-highlight-soft .react-flow__edge-path{filter:drop-shadow(0 0 2px #facc1559);stroke:#eab308bf!important;stroke-width:2.5px!important}@keyframes verso-agent-edge-flow{to{stroke-dashoffset:-17px}}@media (prefers-reduced-motion:reduce){.react-flow__node.verso-agent-highlight>div{animation:none}.react-flow__edge.verso-agent-edge-highlight .react-flow__edge-path{stroke-dasharray:none;animation:none}}.react-flow__controls{overflow:hidden;background:#1e293b!important;border:1px solid #475569!important;border-radius:.375rem!important;box-shadow:0 8px 24px #00000059!important}.react-flow__controls-button{color:#cbd5e1!important;fill:currentColor!important;background:#1e293b!important;border-bottom:1px solid #475569!important}.react-flow__controls-button:last-child{border-bottom:0!important}.react-flow__controls-button:hover{background:#334155!important}.react-flow__controls-button svg{fill:currentColor!important}.verso-markdown{line-height:1.55}.verso-markdown>:first-child{margin-top:0}.verso-markdown>:last-child{margin-bottom:0}.verso-markdown p,.verso-markdown ul,.verso-markdown ol,.verso-markdown pre,.verso-markdown table,.verso-markdown blockquote{margin:.45rem 0}.verso-markdown ul{padding-left:1.25rem;list-style:outside}.verso-markdown ol{padding-left:1.25rem;list-style:decimal}.verso-markdown h1,.verso-markdown h2,.verso-markdown h3{color:#f1f5f9;margin:.7rem 0 .35rem;font-weight:650}.verso-markdown h1{font-size:1rem}.verso-markdown h2{font-size:.9rem}.verso-markdown h3{font-size:.8rem}.verso-markdown code{background:#0f172a;border-radius:.25rem;padding:.1rem .25rem;font-family:ui-monospace,SFMono-Regular,Menlo,Monaco,Consolas,monospace}.verso-markdown pre{background:#020617;border:1px solid #475569;border-radius:.375rem;padding:.65rem;overflow-x:auto}.verso-markdown pre code{background:0 0;padding:0}.verso-markdown table{border-collapse:collapse;width:100%}.verso-markdown th,.verso-markdown td{text-align:left;vertical-align:top;border:1px solid #475569;padding:.35rem .5rem}.verso-markdown th{background:#1e293b}.verso-markdown a{color:#60a5fa;text-decoration:underline}.verso-markdown blockquote{color:#94a3b8;border-left:3px solid #475569;padding-left:.65rem}.verso-pet{z-index:45;pointer-events:none;filter:drop-shadow(0 3px 2px #00000059);width:216px;height:216px;transition:left 7s linear,top 7s linear;position:fixed}.verso-pet-sprite{width:216px;height:216px;image-rendering:pixelated;transform-origin:50%;background-repeat:no-repeat}.verso-pet-sprite-shell{transform-origin:50%;width:216px;height:216px;position:relative}.verso-pet-glitch-layer{visibility:hidden;opacity:0;position:absolute;inset:0}.verso-pet-entering{animation:1.85s cubic-bezier(.16,.72,.24,1) both verso-pet-materialize}.verso-pet-exiting{animation:1.05s cubic-bezier(.55,.08,.8,.35) both verso-pet-dematerialize}.verso-pet-glitch-field{z-index:44;pointer-events:none;background:repeating-linear-gradient(0deg, #22d3ee00 0, #22d3ee00 4px, #22d3ee2e 5px, #ec48991a 7px), radial-gradient(circle at var(--verso-pet-focus-x) var(--verso-pet-focus-y), #ffffff38, #22d3ee1a 18%, transparent 48%);mix-blend-mode:screen;will-change:clip-path, opacity, filter, transform;position:fixed;inset:0}.verso-pet-glitch-field:before,.verso-pet-glitch-field:after{content:\"\";background:repeating-linear-gradient(90deg,#0000 0 9%,#22d3ee1f 9% 9.4%,#0000 9.4% 21%,#f43f5e1a 21% 21.5%);position:absolute;inset:0}.verso-pet-glitch-field:before{animation:.48s ease-in-out infinite alternate verso-screen-slices;transform:translate(-6px)}.verso-pet-glitch-field:after{animation:.61s ease-in-out infinite alternate-reverse verso-screen-slices;transform:translate(7px)}.verso-pet-glitch-field-entering{animation:1.85s cubic-bezier(.2,.75,.25,1) both verso-screen-focus}.verso-pet-glitch-field-exiting{animation:1.05s cubic-bezier(.7,0,.8,.25) both verso-screen-unfocus}.verso-pet-entering .verso-pet-glitch-layer,.verso-pet-exiting .verso-pet-glitch-layer,.verso-pet-ambient-glitch .verso-pet-glitch-layer{visibility:visible}.verso-pet-entering .verso-pet-glitch-cyan,.verso-pet-exiting .verso-pet-glitch-cyan{filter:sepia()saturate(8)hue-rotate(125deg)brightness(1.35);animation:.34s ease-in-out infinite alternate verso-pet-glitch-cyan}.verso-pet-entering .verso-pet-glitch-magenta,.verso-pet-exiting .verso-pet-glitch-magenta{filter:sepia()saturate(9)hue-rotate(265deg)brightness(1.25);animation:.41s ease-in-out infinite alternate-reverse verso-pet-glitch-magenta}.verso-pet-ambient-glitch .verso-pet-sprite-shell{animation:1.35s cubic-bezier(.2,.7,.25,1) both verso-pet-ambient-pulse}.verso-pet-ambient-glitch .verso-pet-glitch-cyan{filter:sepia()saturate(7)hue-rotate(125deg)brightness(1.25);animation:.3s ease-in-out infinite alternate verso-pet-glitch-cyan}.verso-pet-ambient-glitch .verso-pet-glitch-magenta{filter:sepia()saturate(8)hue-rotate(265deg)brightness(1.18);animation:.37s ease-in-out infinite alternate-reverse verso-pet-glitch-magenta}.verso-pet-walking .verso-pet-sprite{background-size:1080px 216px;animation-name:verso-dog-run;animation-duration:.65s;animation-timing-function:steps(5,end);animation-iteration-count:infinite}.verso-pet-sleeping{transition:none}.verso-pet-sleeping .verso-pet-sprite{background-size:1944px 216px;animation-name:verso-dog-sleep;animation-duration:1.2s;animation-timing-function:steps(8,end);animation-fill-mode:forwards}.verso-pet-visiting{transition:left 1.45s cubic-bezier(.2,.72,.25,1),top 1.45s cubic-bezier(.2,.72,.25,1)}.verso-pet-barking .verso-pet-sprite{background-size:1944px 216px;animation:1s steps(9,end) infinite verso-dog-bark}.verso-pet-warning-bubble{color:#fef3c7;border-color:#f59e0b;box-shadow:0 5px 18px #0000004d,0 0 0 2px #f59e0b1f}.verso-pet-pipeline-bubble{color:#cffafe;white-space:normal;border-color:#22d3eeb3;max-width:14rem;font-size:.7rem;line-height:1.35}.verso-pet-bubble{left:var(--verso-pet-bubble-left,-139px);color:#cbd5e1;background:#0f172af0;border:1px solid #475569;border-radius:.75rem .75rem 0;width:max-content;max-width:min(14rem,100vw - 1rem);padding:.35rem .55rem;font-size:.65rem;position:absolute;bottom:162px;box-shadow:0 5px 18px #0000004d}.verso-pet-bubble-below .verso-pet-bubble{border-radius:0 .75rem .75rem;top:162px;bottom:auto}@keyframes verso-dog-run{0%{background-position:0 0}to{background-position:-1080px 0}}@keyframes verso-dog-sleep{0%{background-position:0 0}to{background-position:-1728px 0}}@keyframes verso-dog-bark{0%{background-position:0 0}to{background-position:-1944px 0}}@keyframes verso-pet-materialize{0%{opacity:0;clip-path:inset(49% 0);filter:brightness(2)contrast(1.55)blur(1px);transform:translate(4px)scale(.98)}18%{opacity:.35;clip-path:inset(37% 0 39%);transform:translate(-3px)scale(.985)}36%{opacity:.68;clip-path:inset(25% 0 28%);transform:translate(2px)scale(.99)}56%{opacity:.88;clip-path:inset(12% 0 14%);filter:brightness(1.45)contrast(1.25);transform:translate(-1px)}76%{opacity:1;clip-path:inset(3% 0 4%);filter:brightness(1.15)contrast(1.08)}to{opacity:1;clip-path:inset(0);filter:none;transform:translate(0)}}@keyframes verso-pet-dematerialize{0%{opacity:1;clip-path:inset(0);filter:none}26%{opacity:.9;clip-path:inset(7% 0 8%);transform:translate(-2px)}52%{opacity:.65;clip-path:inset(22% 0 25%);transform:translate(3px)}76%{opacity:.3;clip-path:inset(39% 0 41%);filter:brightness(1.8)contrast(1.45)blur(.7px)}to{opacity:0;clip-path:inset(49% 0);transform:translate(-3px)scale(.98)}}@keyframes verso-pet-glitch-cyan{0%{opacity:.42;clip-path:inset(8% 0 65%);transform:translate(-6px)}48%{opacity:.26;clip-path:inset(43% 0 31%);transform:translate(5px)}to{opacity:.36;clip-path:inset(73% 0 5%);transform:translate(-3px)}}@keyframes verso-pet-glitch-magenta{0%{opacity:.3;clip-path:inset(18% 0 57%);transform:translate(5px)}52%{opacity:.42;clip-path:inset(59% 0 14%);transform:translate(-6px)}to{opacity:.24;clip-path:inset(34% 0 45%);transform:translate(4px)}}@keyframes verso-pet-ambient-pulse{0%,to{filter:none}12%{filter:brightness(1.25)contrast(1.2);transform:translate(0)}24%{filter:brightness(.92)contrast(1.3);transform:translate(-3px)}38%{filter:brightness(1.16)contrast(1.15);transform:translate(3px)}55%{filter:none;transform:translate(-1px)}72%{filter:brightness(1.08)contrast(1.08);transform:translate(1px)}88%{filter:none;transform:translate(0)}}@keyframes verso-screen-focus{0%{opacity:0;clip-path:circle(150vmax at var(--verso-pet-focus-x) var(--verso-pet-focus-y));filter:contrast(1.8)saturate(1.8)hue-rotate(18deg)}14%{opacity:.48;transform:translate(3px)}28%{opacity:.38;transform:translate(-3px)}42%{opacity:.42;clip-path:circle(75vmax at var(--verso-pet-focus-x) var(--verso-pet-focus-y))}64%{opacity:.3;clip-path:circle(34vmax at var(--verso-pet-focus-x) var(--verso-pet-focus-y));filter:contrast(1.45)saturate(1.5)hue-rotate(-12deg)}82%{opacity:.24;clip-path:circle(280px at var(--verso-pet-focus-x) var(--verso-pet-focus-y));transform:translate(1px)}to{opacity:0;clip-path:circle(125px at var(--verso-pet-focus-x) var(--verso-pet-focus-y));filter:none;transform:none}}@keyframes verso-screen-unfocus{0%{opacity:0;clip-path:circle(125px at var(--verso-pet-focus-x) var(--verso-pet-focus-y))}25%{opacity:.5}70%{opacity:.35;clip-path:circle(65vmax at var(--verso-pet-focus-x) var(--verso-pet-focus-y));filter:contrast(1.6)hue-rotate(20deg)}to{opacity:0;clip-path:circle(150vmax at var(--verso-pet-focus-x) var(--verso-pet-focus-y))}}@keyframes verso-screen-slices{0%{clip-path:inset(4% 0 74%);opacity:.8}33%{clip-path:inset(46% 0 31%);opacity:.35}66%{clip-path:inset(77% 0 8%);opacity:.65}to{clip-path:inset(28% 0 54%);opacity:.42}}@media (prefers-reduced-motion:reduce){.verso-pet{transition:none}.verso-pet-sprite{animation:none!important}.verso-pet-entering,.verso-pet-exiting,.verso-pet-glitch-layer,.verso-pet-glitch-field,.verso-pet-glitch-field:before,.verso-pet-glitch-field:after,.verso-pet-ambient-glitch .verso-pet-sprite-shell{clip-path:none;filter:none;animation:none!important}.verso-pet-glitch-field{display:none}}.placeholder\\:text-slate-500::placeholder{--tw-text-opacity:1;color:rgb(100 116 139/var(--tw-text-opacity,1))}.placeholder\\:text-slate-600::placeholder{--tw-text-opacity:1;color:rgb(71 85 105/var(--tw-text-opacity,1))}.last\\:border-0:last-child{border-width:0}.hover\\:border-amber-400:hover{--tw-border-opacity:1;border-color:rgb(251 191 36/var(--tw-border-opacity,1))}.hover\\:border-blue-500:hover{--tw-border-opacity:1;border-color:rgb(59 130 246/var(--tw-border-opacity,1))}.hover\\:border-cyan-500:hover{--tw-border-opacity:1;border-color:rgb(6 182 212/var(--tw-border-opacity,1))}.hover\\:border-green-500:hover{--tw-border-opacity:1;border-color:rgb(34 197 94/var(--tw-border-opacity,1))}.hover\\:border-slate-600:hover{--tw-border-opacity:1;border-color:rgb(71 85 105/var(--tw-border-opacity,1))}.hover\\:bg-amber-400:hover{--tw-bg-opacity:1;background-color:rgb(251 191 36/var(--tw-bg-opacity,1))}.hover\\:bg-amber-500:hover{--tw-bg-opacity:1;background-color:rgb(245 158 11/var(--tw-bg-opacity,1))}.hover\\:bg-amber-600:hover{--tw-bg-opacity:1;background-color:rgb(217 119 6/var(--tw-bg-opacity,1))}.hover\\:bg-amber-900:hover{--tw-bg-opacity:1;background-color:rgb(120 53 15/var(--tw-bg-opacity,1))}.hover\\:bg-amber-950:hover{--tw-bg-opacity:1;background-color:rgb(69 26 3/var(--tw-bg-opacity,1))}.hover\\:bg-blue-500:hover{--tw-bg-opacity:1;background-color:rgb(59 130 246/var(--tw-bg-opacity,1))}.hover\\:bg-blue-600:hover{--tw-bg-opacity:1;background-color:rgb(37 99 235/var(--tw-bg-opacity,1))}.hover\\:bg-blue-900:hover{--tw-bg-opacity:1;background-color:rgb(30 58 138/var(--tw-bg-opacity,1))}.hover\\:bg-cyan-600:hover{--tw-bg-opacity:1;background-color:rgb(8 145 178/var(--tw-bg-opacity,1))}.hover\\:bg-cyan-700:hover{--tw-bg-opacity:1;background-color:rgb(14 116 144/var(--tw-bg-opacity,1))}.hover\\:bg-cyan-950:hover{--tw-bg-opacity:1;background-color:rgb(8 51 68/var(--tw-bg-opacity,1))}.hover\\:bg-emerald-600:hover{--tw-bg-opacity:1;background-color:rgb(5 150 105/var(--tw-bg-opacity,1))}.hover\\:bg-emerald-900:hover{--tw-bg-opacity:1;background-color:rgb(6 78 59/var(--tw-bg-opacity,1))}.hover\\:bg-gray-600:hover{--tw-bg-opacity:1;background-color:rgb(75 85 99/var(--tw-bg-opacity,1))}.hover\\:bg-gray-700:hover{--tw-bg-opacity:1;background-color:rgb(55 65 81/var(--tw-bg-opacity,1))}.hover\\:bg-gray-800:hover{--tw-bg-opacity:1;background-color:rgb(31 41 55/var(--tw-bg-opacity,1))}.hover\\:bg-green-700:hover{--tw-bg-opacity:1;background-color:rgb(21 128 61/var(--tw-bg-opacity,1))}.hover\\:bg-indigo-950:hover{--tw-bg-opacity:1;background-color:rgb(30 27 75/var(--tw-bg-opacity,1))}.hover\\:bg-orange-700:hover{--tw-bg-opacity:1;background-color:rgb(194 65 12/var(--tw-bg-opacity,1))}.hover\\:bg-purple-500:hover{--tw-bg-opacity:1;background-color:rgb(168 85 247/var(--tw-bg-opacity,1))}.hover\\:bg-purple-700:hover{--tw-bg-opacity:1;background-color:rgb(126 34 206/var(--tw-bg-opacity,1))}.hover\\:bg-red-600:hover{--tw-bg-opacity:1;background-color:rgb(220 38 38/var(--tw-bg-opacity,1))}.hover\\:bg-red-700:hover{--tw-bg-opacity:1;background-color:rgb(185 28 28/var(--tw-bg-opacity,1))}.hover\\:bg-red-800:hover{--tw-bg-opacity:1;background-color:rgb(153 27 27/var(--tw-bg-opacity,1))}.hover\\:bg-red-900:hover{--tw-bg-opacity:1;background-color:rgb(127 29 29/var(--tw-bg-opacity,1))}.hover\\:bg-red-950:hover{--tw-bg-opacity:1;background-color:rgb(69 10 10/var(--tw-bg-opacity,1))}.hover\\:bg-sky-700:hover{--tw-bg-opacity:1;background-color:rgb(3 105 161/var(--tw-bg-opacity,1))}.hover\\:bg-sky-800:hover{--tw-bg-opacity:1;background-color:rgb(7 89 133/var(--tw-bg-opacity,1))}.hover\\:bg-sky-950:hover{--tw-bg-opacity:1;background-color:rgb(8 47 73/var(--tw-bg-opacity,1))}.hover\\:bg-slate-600:hover{--tw-bg-opacity:1;background-color:rgb(71 85 105/var(--tw-bg-opacity,1))}.hover\\:bg-slate-700:hover{--tw-bg-opacity:1;background-color:rgb(51 65 85/var(--tw-bg-opacity,1))}.hover\\:bg-slate-800:hover{--tw-bg-opacity:1;background-color:rgb(30 41 59/var(--tw-bg-opacity,1))}.hover\\:bg-slate-900:hover{--tw-bg-opacity:1;background-color:rgb(15 23 42/var(--tw-bg-opacity,1))}.hover\\:bg-violet-600:hover{--tw-bg-opacity:1;background-color:rgb(124 58 237/var(--tw-bg-opacity,1))}.hover\\:bg-violet-950:hover{--tw-bg-opacity:1;background-color:rgb(46 16 101/var(--tw-bg-opacity,1))}.hover\\:bg-white\\/10:hover{background-color:#ffffff1a}.hover\\:bg-yellow-400:hover{--tw-bg-opacity:1;background-color:rgb(250 204 21/var(--tw-bg-opacity,1))}.hover\\:bg-yellow-700:hover{--tw-bg-opacity:1;background-color:rgb(161 98 7/var(--tw-bg-opacity,1))}.hover\\:text-amber-200:hover{--tw-text-opacity:1;color:rgb(253 230 138/var(--tw-text-opacity,1))}.hover\\:text-blue-300:hover{--tw-text-opacity:1;color:rgb(147 197 253/var(--tw-text-opacity,1))}.hover\\:text-blue-400:hover{--tw-text-opacity:1;color:rgb(96 165 250/var(--tw-text-opacity,1))}.hover\\:text-gray-300:hover{--tw-text-opacity:1;color:rgb(209 213 219/var(--tw-text-opacity,1))}.hover\\:text-purple-300:hover{--tw-text-opacity:1;color:rgb(216 180 254/var(--tw-text-opacity,1))}.hover\\:text-slate-100:hover{--tw-text-opacity:1;color:rgb(241 245 249/var(--tw-text-opacity,1))}.hover\\:text-slate-200:hover{--tw-text-opacity:1;color:rgb(226 232 240/var(--tw-text-opacity,1))}.hover\\:text-slate-300:hover{--tw-text-opacity:1;color:rgb(203 213 225/var(--tw-text-opacity,1))}.hover\\:text-white:hover{--tw-text-opacity:1;color:rgb(255 255 255/var(--tw-text-opacity,1))}.focus\\:border-blue-500:focus{--tw-border-opacity:1;border-color:rgb(59 130 246/var(--tw-border-opacity,1))}.focus\\:bg-blue-600:focus{--tw-bg-opacity:1;background-color:rgb(37 99 235/var(--tw-bg-opacity,1))}.focus\\:outline-none:focus{outline-offset:2px;outline:2px solid #0000}.focus\\:ring-1:focus{--tw-ring-offset-shadow:var(--tw-ring-inset) 0 0 0 var(--tw-ring-offset-width) var(--tw-ring-offset-color);--tw-ring-shadow:var(--tw-ring-inset) 0 0 0 calc(1px + var(--tw-ring-offset-width)) var(--tw-ring-color);box-shadow:var(--tw-ring-offset-shadow), var(--tw-ring-shadow), var(--tw-shadow,0 0 #0000)}.focus\\:ring-blue-500:focus{--tw-ring-opacity:1;--tw-ring-color:rgb(59 130 246/var(--tw-ring-opacity,1))}.focus\\:ring-blue-500\\/40:focus{--tw-ring-color:#3b82f666}.focus\\:ring-green-500:focus{--tw-ring-opacity:1;--tw-ring-color:rgb(34 197 94/var(--tw-ring-opacity,1))}.focus\\:ring-purple-500:focus{--tw-ring-opacity:1;--tw-ring-color:rgb(168 85 247/var(--tw-ring-opacity,1))}.active\\:cursor-grabbing:active{cursor:grabbing}.disabled\\:cursor-not-allowed:disabled{cursor:not-allowed}.disabled\\:opacity-30:disabled{opacity:.3}.disabled\\:opacity-40:disabled{opacity:.4}.disabled\\:opacity-50:disabled{opacity:.5}.group:hover .group-hover\\:bg-white{--tw-bg-opacity:1;background-color:rgb(255 255 255/var(--tw-bg-opacity,1))}@media (width>=640px){.sm\\:grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}}@media (width>=768px){.md\\:grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}.md\\:grid-cols-4{grid-template-columns:repeat(4,minmax(0,1fr))}}@media (width>=1024px){.lg\\:grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}.lg\\:grid-cols-4{grid-template-columns:repeat(4,minmax(0,1fr))}}@media (width>=1280px){.xl\\:grid-cols-2{grid-template-columns:repeat(2,minmax(0,1fr))}.xl\\:grid-cols-6{grid-template-columns:repeat(6,minmax(0,1fr))}.xl\\:grid-cols-\\[18rem_minmax\\(0\\,1fr\\)\\]{grid-template-columns:18rem minmax(0,1fr)}}", v = /* @__PURE__ */ o(((e) => {
	var t = u(), n = Symbol.for("react.element"), r = Symbol.for("react.fragment"), i = Object.prototype.hasOwnProperty, a = t.__SECRET_INTERNALS_DO_NOT_USE_OR_YOU_WILL_BE_FIRED.ReactCurrentOwner, o = {
		key: !0,
		ref: !0,
		__self: !0,
		__source: !0
	};
	function s(e, t, r) {
		var s, c = {}, l = null, u = null;
		for (s in r !== void 0 && (l = "" + r), t.key !== void 0 && (l = "" + t.key), t.ref !== void 0 && (u = t.ref), t) i.call(t, s) && !o.hasOwnProperty(s) && (c[s] = t[s]);
		if (e && e.defaultProps) for (s in t = e.defaultProps, t) c[s] === void 0 && (c[s] = t[s]);
		return {
			$$typeof: n,
			type: e,
			key: l,
			ref: u,
			props: c,
			_owner: a.current
		};
	}
	e.Fragment = r, e.jsx = s, e.jsxs = s;
})), y = /* @__PURE__ */ o(((e, t) => {
	t.exports = v();
})), b = /* @__PURE__ */ c(u(), 1), x = y();
function S(e) {
	if (typeof e == "string" || typeof e == "number") return "" + e;
	let t = "";
	if (Array.isArray(e)) for (let n = 0, r; n < e.length; n++) (r = S(e[n])) !== "" && (t += (t && " ") + r);
	else for (let n in e) e[n] && (t += (t && " ") + n);
	return t;
}
//#endregion
//#region node_modules/d3-dispatch/src/dispatch.js
var C = { value: () => {} };
function w() {
	for (var e = 0, t = arguments.length, n = {}, r; e < t; ++e) {
		if (!(r = arguments[e] + "") || r in n || /[\s.]/.test(r)) throw Error("illegal type: " + r);
		n[r] = [];
	}
	return new T(n);
}
function T(e) {
	this._ = e;
}
function E(e, t) {
	return e.trim().split(/^|\s+/).map(function(e) {
		var n = "", r = e.indexOf(".");
		if (r >= 0 && (n = e.slice(r + 1), e = e.slice(0, r)), e && !t.hasOwnProperty(e)) throw Error("unknown type: " + e);
		return {
			type: e,
			name: n
		};
	});
}
T.prototype = w.prototype = {
	constructor: T,
	on: function(e, t) {
		var n = this._, r = E(e + "", n), i, a = -1, o = r.length;
		if (arguments.length < 2) {
			for (; ++a < o;) if ((i = (e = r[a]).type) && (i = D(n[i], e.name))) return i;
			return;
		}
		if (t != null && typeof t != "function") throw Error("invalid callback: " + t);
		for (; ++a < o;) if (i = (e = r[a]).type) n[i] = O(n[i], e.name, t);
		else if (t == null) for (i in n) n[i] = O(n[i], e.name, null);
		return this;
	},
	copy: function() {
		var e = {}, t = this._;
		for (var n in t) e[n] = t[n].slice();
		return new T(e);
	},
	call: function(e, t) {
		if ((i = arguments.length - 2) > 0) for (var n = Array(i), r = 0, i, a; r < i; ++r) n[r] = arguments[r + 2];
		if (!this._.hasOwnProperty(e)) throw Error("unknown type: " + e);
		for (a = this._[e], r = 0, i = a.length; r < i; ++r) a[r].value.apply(t, n);
	},
	apply: function(e, t, n) {
		if (!this._.hasOwnProperty(e)) throw Error("unknown type: " + e);
		for (var r = this._[e], i = 0, a = r.length; i < a; ++i) r[i].value.apply(t, n);
	}
};
function D(e, t) {
	for (var n = 0, r = e.length, i; n < r; ++n) if ((i = e[n]).name === t) return i.value;
}
function O(e, t, n) {
	for (var r = 0, i = e.length; r < i; ++r) if (e[r].name === t) {
		e[r] = C, e = e.slice(0, r).concat(e.slice(r + 1));
		break;
	}
	return n != null && e.push({
		name: t,
		value: n
	}), e;
}
var k = {
	svg: "http://www.w3.org/2000/svg",
	xhtml: "http://www.w3.org/1999/xhtml",
	xlink: "http://www.w3.org/1999/xlink",
	xml: "http://www.w3.org/XML/1998/namespace",
	xmlns: "http://www.w3.org/2000/xmlns/"
};
//#endregion
//#region node_modules/d3-selection/src/namespace.js
function A(e) {
	var t = e += "", n = t.indexOf(":");
	return n >= 0 && (t = e.slice(0, n)) !== "xmlns" && (e = e.slice(n + 1)), k.hasOwnProperty(t) ? {
		space: k[t],
		local: e
	} : e;
}
//#endregion
//#region node_modules/d3-selection/src/creator.js
function j(e) {
	return function() {
		var t = this.ownerDocument, n = this.namespaceURI;
		return n === "http://www.w3.org/1999/xhtml" && t.documentElement.namespaceURI === "http://www.w3.org/1999/xhtml" ? t.createElement(e) : t.createElementNS(n, e);
	};
}
function M(e) {
	return function() {
		return this.ownerDocument.createElementNS(e.space, e.local);
	};
}
function N(e) {
	var t = A(e);
	return (t.local ? M : j)(t);
}
//#endregion
//#region node_modules/d3-selection/src/selector.js
function P() {}
function F(e) {
	return e == null ? P : function() {
		return this.querySelector(e);
	};
}
//#endregion
//#region node_modules/d3-selection/src/selection/select.js
function I(e) {
	typeof e != "function" && (e = F(e));
	for (var t = this._groups, n = t.length, r = Array(n), i = 0; i < n; ++i) for (var a = t[i], o = a.length, s = r[i] = Array(o), c, l, u = 0; u < o; ++u) (c = a[u]) && (l = e.call(c, c.__data__, u, a)) && ("__data__" in c && (l.__data__ = c.__data__), s[u] = l);
	return new Lt(r, this._parents);
}
//#endregion
//#region node_modules/d3-selection/src/array.js
function ee(e) {
	return e == null ? [] : Array.isArray(e) ? e : Array.from(e);
}
//#endregion
//#region node_modules/d3-selection/src/selectorAll.js
function L() {
	return [];
}
function R(e) {
	return e == null ? L : function() {
		return this.querySelectorAll(e);
	};
}
//#endregion
//#region node_modules/d3-selection/src/selection/selectAll.js
function z(e) {
	return function() {
		return ee(e.apply(this, arguments));
	};
}
function B(e) {
	e = typeof e == "function" ? z(e) : R(e);
	for (var t = this._groups, n = t.length, r = [], i = [], a = 0; a < n; ++a) for (var o = t[a], s = o.length, c, l = 0; l < s; ++l) (c = o[l]) && (r.push(e.call(c, c.__data__, l, o)), i.push(c));
	return new Lt(r, i);
}
//#endregion
//#region node_modules/d3-selection/src/matcher.js
function te(e) {
	return function() {
		return this.matches(e);
	};
}
function ne(e) {
	return function(t) {
		return t.matches(e);
	};
}
//#endregion
//#region node_modules/d3-selection/src/selection/selectChild.js
var re = Array.prototype.find;
function ie(e) {
	return function() {
		return re.call(this.children, e);
	};
}
function ae() {
	return this.firstElementChild;
}
function oe(e) {
	return this.select(e == null ? ae : ie(typeof e == "function" ? e : ne(e)));
}
//#endregion
//#region node_modules/d3-selection/src/selection/selectChildren.js
var se = Array.prototype.filter;
function ce() {
	return Array.from(this.children);
}
function le(e) {
	return function() {
		return se.call(this.children, e);
	};
}
function ue(e) {
	return this.selectAll(e == null ? ce : le(typeof e == "function" ? e : ne(e)));
}
//#endregion
//#region node_modules/d3-selection/src/selection/filter.js
function de(e) {
	typeof e != "function" && (e = te(e));
	for (var t = this._groups, n = t.length, r = Array(n), i = 0; i < n; ++i) for (var a = t[i], o = a.length, s = r[i] = [], c, l = 0; l < o; ++l) (c = a[l]) && e.call(c, c.__data__, l, a) && s.push(c);
	return new Lt(r, this._parents);
}
//#endregion
//#region node_modules/d3-selection/src/selection/sparse.js
function fe(e) {
	return Array(e.length);
}
//#endregion
//#region node_modules/d3-selection/src/selection/enter.js
function pe() {
	return new Lt(this._enter || this._groups.map(fe), this._parents);
}
function me(e, t) {
	this.ownerDocument = e.ownerDocument, this.namespaceURI = e.namespaceURI, this._next = null, this._parent = e, this.__data__ = t;
}
me.prototype = {
	constructor: me,
	appendChild: function(e) {
		return this._parent.insertBefore(e, this._next);
	},
	insertBefore: function(e, t) {
		return this._parent.insertBefore(e, t);
	},
	querySelector: function(e) {
		return this._parent.querySelector(e);
	},
	querySelectorAll: function(e) {
		return this._parent.querySelectorAll(e);
	}
};
//#endregion
//#region node_modules/d3-selection/src/constant.js
function he(e) {
	return function() {
		return e;
	};
}
//#endregion
//#region node_modules/d3-selection/src/selection/data.js
function ge(e, t, n, r, i, a) {
	for (var o = 0, s, c = t.length, l = a.length; o < l; ++o) (s = t[o]) ? (s.__data__ = a[o], r[o] = s) : n[o] = new me(e, a[o]);
	for (; o < c; ++o) (s = t[o]) && (i[o] = s);
}
function _e(e, t, n, r, i, a, o) {
	var s, c, l = /* @__PURE__ */ new Map(), u = t.length, d = a.length, f = Array(u), p;
	for (s = 0; s < u; ++s) (c = t[s]) && (f[s] = p = o.call(c, c.__data__, s, t) + "", l.has(p) ? i[s] = c : l.set(p, c));
	for (s = 0; s < d; ++s) p = o.call(e, a[s], s, a) + "", (c = l.get(p)) ? (r[s] = c, c.__data__ = a[s], l.delete(p)) : n[s] = new me(e, a[s]);
	for (s = 0; s < u; ++s) (c = t[s]) && l.get(f[s]) === c && (i[s] = c);
}
function ve(e) {
	return e.__data__;
}
function ye(e, t) {
	if (!arguments.length) return Array.from(this, ve);
	var n = t ? _e : ge, r = this._parents, i = this._groups;
	typeof e != "function" && (e = he(e));
	for (var a = i.length, o = Array(a), s = Array(a), c = Array(a), l = 0; l < a; ++l) {
		var u = r[l], d = i[l], f = d.length, p = be(e.call(u, u && u.__data__, l, r)), m = p.length, h = s[l] = Array(m), g = o[l] = Array(m);
		n(u, d, h, g, c[l] = Array(f), p, t);
		for (var _ = 0, v = 0, y, b; _ < m; ++_) if (y = h[_]) {
			for (_ >= v && (v = _ + 1); !(b = g[v]) && ++v < m;);
			y._next = b || null;
		}
	}
	return o = new Lt(o, r), o._enter = s, o._exit = c, o;
}
function be(e) {
	return typeof e == "object" && "length" in e ? e : Array.from(e);
}
//#endregion
//#region node_modules/d3-selection/src/selection/exit.js
function xe() {
	return new Lt(this._exit || this._groups.map(fe), this._parents);
}
//#endregion
//#region node_modules/d3-selection/src/selection/join.js
function Se(e, t, n) {
	var r = this.enter(), i = this, a = this.exit();
	return typeof e == "function" ? (r = e(r), r &&= r.selection()) : r = r.append(e + ""), t != null && (i = t(i), i &&= i.selection()), n == null ? a.remove() : n(a), r && i ? r.merge(i).order() : i;
}
//#endregion
//#region node_modules/d3-selection/src/selection/merge.js
function Ce(e) {
	for (var t = e.selection ? e.selection() : e, n = this._groups, r = t._groups, i = n.length, a = r.length, o = Math.min(i, a), s = Array(i), c = 0; c < o; ++c) for (var l = n[c], u = r[c], d = l.length, f = s[c] = Array(d), p, m = 0; m < d; ++m) (p = l[m] || u[m]) && (f[m] = p);
	for (; c < i; ++c) s[c] = n[c];
	return new Lt(s, this._parents);
}
//#endregion
//#region node_modules/d3-selection/src/selection/order.js
function we() {
	for (var e = this._groups, t = -1, n = e.length; ++t < n;) for (var r = e[t], i = r.length - 1, a = r[i], o; --i >= 0;) (o = r[i]) && (a && o.compareDocumentPosition(a) ^ 4 && a.parentNode.insertBefore(o, a), a = o);
	return this;
}
//#endregion
//#region node_modules/d3-selection/src/selection/sort.js
function Te(e) {
	e ||= Ee;
	function t(t, n) {
		return t && n ? e(t.__data__, n.__data__) : !t - !n;
	}
	for (var n = this._groups, r = n.length, i = Array(r), a = 0; a < r; ++a) {
		for (var o = n[a], s = o.length, c = i[a] = Array(s), l, u = 0; u < s; ++u) (l = o[u]) && (c[u] = l);
		c.sort(t);
	}
	return new Lt(i, this._parents).order();
}
function Ee(e, t) {
	return e < t ? -1 : e > t ? 1 : e >= t ? 0 : NaN;
}
//#endregion
//#region node_modules/d3-selection/src/selection/call.js
function De() {
	var e = arguments[0];
	return arguments[0] = this, e.apply(null, arguments), this;
}
//#endregion
//#region node_modules/d3-selection/src/selection/nodes.js
function Oe() {
	return Array.from(this);
}
//#endregion
//#region node_modules/d3-selection/src/selection/node.js
function ke() {
	for (var e = this._groups, t = 0, n = e.length; t < n; ++t) for (var r = e[t], i = 0, a = r.length; i < a; ++i) {
		var o = r[i];
		if (o) return o;
	}
	return null;
}
//#endregion
//#region node_modules/d3-selection/src/selection/size.js
function Ae() {
	let e = 0;
	for (let t of this) ++e;
	return e;
}
//#endregion
//#region node_modules/d3-selection/src/selection/empty.js
function je() {
	return !this.node();
}
//#endregion
//#region node_modules/d3-selection/src/selection/each.js
function Me(e) {
	for (var t = this._groups, n = 0, r = t.length; n < r; ++n) for (var i = t[n], a = 0, o = i.length, s; a < o; ++a) (s = i[a]) && e.call(s, s.__data__, a, i);
	return this;
}
//#endregion
//#region node_modules/d3-selection/src/selection/attr.js
function Ne(e) {
	return function() {
		this.removeAttribute(e);
	};
}
function Pe(e) {
	return function() {
		this.removeAttributeNS(e.space, e.local);
	};
}
function Fe(e, t) {
	return function() {
		this.setAttribute(e, t);
	};
}
function Ie(e, t) {
	return function() {
		this.setAttributeNS(e.space, e.local, t);
	};
}
function Le(e, t) {
	return function() {
		var n = t.apply(this, arguments);
		n == null ? this.removeAttribute(e) : this.setAttribute(e, n);
	};
}
function Re(e, t) {
	return function() {
		var n = t.apply(this, arguments);
		n == null ? this.removeAttributeNS(e.space, e.local) : this.setAttributeNS(e.space, e.local, n);
	};
}
function ze(e, t) {
	var n = A(e);
	if (arguments.length < 2) {
		var r = this.node();
		return n.local ? r.getAttributeNS(n.space, n.local) : r.getAttribute(n);
	}
	return this.each((t == null ? n.local ? Pe : Ne : typeof t == "function" ? n.local ? Re : Le : n.local ? Ie : Fe)(n, t));
}
//#endregion
//#region node_modules/d3-selection/src/window.js
function Be(e) {
	return e.ownerDocument && e.ownerDocument.defaultView || e.document && e || e.defaultView;
}
//#endregion
//#region node_modules/d3-selection/src/selection/style.js
function Ve(e) {
	return function() {
		this.style.removeProperty(e);
	};
}
function He(e, t, n) {
	return function() {
		this.style.setProperty(e, t, n);
	};
}
function Ue(e, t, n) {
	return function() {
		var r = t.apply(this, arguments);
		r == null ? this.style.removeProperty(e) : this.style.setProperty(e, r, n);
	};
}
function We(e, t, n) {
	return arguments.length > 1 ? this.each((t == null ? Ve : typeof t == "function" ? Ue : He)(e, t, n ?? "")) : Ge(this.node(), e);
}
function Ge(e, t) {
	return e.style.getPropertyValue(t) || Be(e).getComputedStyle(e, null).getPropertyValue(t);
}
//#endregion
//#region node_modules/d3-selection/src/selection/property.js
function Ke(e) {
	return function() {
		delete this[e];
	};
}
function qe(e, t) {
	return function() {
		this[e] = t;
	};
}
function Je(e, t) {
	return function() {
		var n = t.apply(this, arguments);
		n == null ? delete this[e] : this[e] = n;
	};
}
function Ye(e, t) {
	return arguments.length > 1 ? this.each((t == null ? Ke : typeof t == "function" ? Je : qe)(e, t)) : this.node()[e];
}
//#endregion
//#region node_modules/d3-selection/src/selection/classed.js
function Xe(e) {
	return e.trim().split(/^|\s+/);
}
function Ze(e) {
	return e.classList || new Qe(e);
}
function Qe(e) {
	this._node = e, this._names = Xe(e.getAttribute("class") || "");
}
Qe.prototype = {
	add: function(e) {
		this._names.indexOf(e) < 0 && (this._names.push(e), this._node.setAttribute("class", this._names.join(" ")));
	},
	remove: function(e) {
		var t = this._names.indexOf(e);
		t >= 0 && (this._names.splice(t, 1), this._node.setAttribute("class", this._names.join(" ")));
	},
	contains: function(e) {
		return this._names.indexOf(e) >= 0;
	}
};
function $e(e, t) {
	for (var n = Ze(e), r = -1, i = t.length; ++r < i;) n.add(t[r]);
}
function et(e, t) {
	for (var n = Ze(e), r = -1, i = t.length; ++r < i;) n.remove(t[r]);
}
function tt(e) {
	return function() {
		$e(this, e);
	};
}
function nt(e) {
	return function() {
		et(this, e);
	};
}
function rt(e, t) {
	return function() {
		(t.apply(this, arguments) ? $e : et)(this, e);
	};
}
function it(e, t) {
	var n = Xe(e + "");
	if (arguments.length < 2) {
		for (var r = Ze(this.node()), i = -1, a = n.length; ++i < a;) if (!r.contains(n[i])) return !1;
		return !0;
	}
	return this.each((typeof t == "function" ? rt : t ? tt : nt)(n, t));
}
//#endregion
//#region node_modules/d3-selection/src/selection/text.js
function at() {
	this.textContent = "";
}
function ot(e) {
	return function() {
		this.textContent = e;
	};
}
function st(e) {
	return function() {
		var t = e.apply(this, arguments);
		this.textContent = t ?? "";
	};
}
function ct(e) {
	return arguments.length ? this.each(e == null ? at : (typeof e == "function" ? st : ot)(e)) : this.node().textContent;
}
//#endregion
//#region node_modules/d3-selection/src/selection/html.js
function lt() {
	this.innerHTML = "";
}
function ut(e) {
	return function() {
		this.innerHTML = e;
	};
}
function dt(e) {
	return function() {
		var t = e.apply(this, arguments);
		this.innerHTML = t ?? "";
	};
}
function ft(e) {
	return arguments.length ? this.each(e == null ? lt : (typeof e == "function" ? dt : ut)(e)) : this.node().innerHTML;
}
//#endregion
//#region node_modules/d3-selection/src/selection/raise.js
function pt() {
	this.nextSibling && this.parentNode.appendChild(this);
}
function mt() {
	return this.each(pt);
}
//#endregion
//#region node_modules/d3-selection/src/selection/lower.js
function ht() {
	this.previousSibling && this.parentNode.insertBefore(this, this.parentNode.firstChild);
}
function gt() {
	return this.each(ht);
}
//#endregion
//#region node_modules/d3-selection/src/selection/append.js
function _t(e) {
	var t = typeof e == "function" ? e : N(e);
	return this.select(function() {
		return this.appendChild(t.apply(this, arguments));
	});
}
//#endregion
//#region node_modules/d3-selection/src/selection/insert.js
function vt() {
	return null;
}
function yt(e, t) {
	var n = typeof e == "function" ? e : N(e), r = t == null ? vt : typeof t == "function" ? t : F(t);
	return this.select(function() {
		return this.insertBefore(n.apply(this, arguments), r.apply(this, arguments) || null);
	});
}
//#endregion
//#region node_modules/d3-selection/src/selection/remove.js
function bt() {
	var e = this.parentNode;
	e && e.removeChild(this);
}
function xt() {
	return this.each(bt);
}
//#endregion
//#region node_modules/d3-selection/src/selection/clone.js
function St() {
	var e = this.cloneNode(!1), t = this.parentNode;
	return t ? t.insertBefore(e, this.nextSibling) : e;
}
function Ct() {
	var e = this.cloneNode(!0), t = this.parentNode;
	return t ? t.insertBefore(e, this.nextSibling) : e;
}
function wt(e) {
	return this.select(e ? Ct : St);
}
//#endregion
//#region node_modules/d3-selection/src/selection/datum.js
function Tt(e) {
	return arguments.length ? this.property("__data__", e) : this.node().__data__;
}
//#endregion
//#region node_modules/d3-selection/src/selection/on.js
function Et(e) {
	return function(t) {
		e.call(this, t, this.__data__);
	};
}
function Dt(e) {
	return e.trim().split(/^|\s+/).map(function(e) {
		var t = "", n = e.indexOf(".");
		return n >= 0 && (t = e.slice(n + 1), e = e.slice(0, n)), {
			type: e,
			name: t
		};
	});
}
function Ot(e) {
	return function() {
		var t = this.__on;
		if (t) {
			for (var n = 0, r = -1, i = t.length, a; n < i; ++n) a = t[n], (!e.type || a.type === e.type) && a.name === e.name ? this.removeEventListener(a.type, a.listener, a.options) : t[++r] = a;
			++r ? t.length = r : delete this.__on;
		}
	};
}
function kt(e, t, n) {
	return function() {
		var r = this.__on, i, a = Et(t);
		if (r) {
			for (var o = 0, s = r.length; o < s; ++o) if ((i = r[o]).type === e.type && i.name === e.name) {
				this.removeEventListener(i.type, i.listener, i.options), this.addEventListener(i.type, i.listener = a, i.options = n), i.value = t;
				return;
			}
		}
		this.addEventListener(e.type, a, n), i = {
			type: e.type,
			name: e.name,
			value: t,
			listener: a,
			options: n
		}, r ? r.push(i) : this.__on = [i];
	};
}
function At(e, t, n) {
	var r = Dt(e + ""), i, a = r.length, o;
	if (arguments.length < 2) {
		var s = this.node().__on;
		if (s) {
			for (var c = 0, l = s.length, u; c < l; ++c) for (i = 0, u = s[c]; i < a; ++i) if ((o = r[i]).type === u.type && o.name === u.name) return u.value;
		}
		return;
	}
	for (s = t ? kt : Ot, i = 0; i < a; ++i) this.each(s(r[i], t, n));
	return this;
}
//#endregion
//#region node_modules/d3-selection/src/selection/dispatch.js
function jt(e, t, n) {
	var r = Be(e), i = r.CustomEvent;
	typeof i == "function" ? i = new i(t, n) : (i = r.document.createEvent("Event"), n ? (i.initEvent(t, n.bubbles, n.cancelable), i.detail = n.detail) : i.initEvent(t, !1, !1)), e.dispatchEvent(i);
}
function Mt(e, t) {
	return function() {
		return jt(this, e, t);
	};
}
function Nt(e, t) {
	return function() {
		return jt(this, e, t.apply(this, arguments));
	};
}
function Pt(e, t) {
	return this.each((typeof t == "function" ? Nt : Mt)(e, t));
}
//#endregion
//#region node_modules/d3-selection/src/selection/iterator.js
function* Ft() {
	for (var e = this._groups, t = 0, n = e.length; t < n; ++t) for (var r = e[t], i = 0, a = r.length, o; i < a; ++i) (o = r[i]) && (yield o);
}
//#endregion
//#region node_modules/d3-selection/src/selection/index.js
var It = [null];
function Lt(e, t) {
	this._groups = e, this._parents = t;
}
function Rt() {
	return new Lt([[document.documentElement]], It);
}
function zt() {
	return this;
}
Lt.prototype = Rt.prototype = {
	constructor: Lt,
	select: I,
	selectAll: B,
	selectChild: oe,
	selectChildren: ue,
	filter: de,
	data: ye,
	enter: pe,
	exit: xe,
	join: Se,
	merge: Ce,
	selection: zt,
	order: we,
	sort: Te,
	call: De,
	nodes: Oe,
	node: ke,
	size: Ae,
	empty: je,
	each: Me,
	attr: ze,
	style: We,
	property: Ye,
	classed: it,
	text: ct,
	html: ft,
	raise: mt,
	lower: gt,
	append: _t,
	insert: yt,
	remove: xt,
	clone: wt,
	datum: Tt,
	on: At,
	dispatch: Pt,
	[Symbol.iterator]: Ft
};
//#endregion
//#region node_modules/d3-selection/src/select.js
function Bt(e) {
	return typeof e == "string" ? new Lt([[document.querySelector(e)]], [document.documentElement]) : new Lt([[e]], It);
}
//#endregion
//#region node_modules/d3-selection/src/sourceEvent.js
function V(e) {
	let t;
	for (; t = e.sourceEvent;) e = t;
	return e;
}
//#endregion
//#region node_modules/d3-selection/src/pointer.js
function Vt(e, t) {
	if (e = V(e), t === void 0 && (t = e.currentTarget), t) {
		var n = t.ownerSVGElement || t;
		if (n.createSVGPoint) {
			var r = n.createSVGPoint();
			return r.x = e.clientX, r.y = e.clientY, r = r.matrixTransform(t.getScreenCTM().inverse()), [r.x, r.y];
		}
		if (t.getBoundingClientRect) {
			var i = t.getBoundingClientRect();
			return [e.clientX - i.left - t.clientLeft, e.clientY - i.top - t.clientTop];
		}
	}
	return [e.pageX, e.pageY];
}
//#endregion
//#region node_modules/d3-drag/src/noevent.js
var Ht = { passive: !1 }, Ut = {
	capture: !0,
	passive: !1
};
function Wt(e) {
	e.stopImmediatePropagation();
}
function Gt(e) {
	e.preventDefault(), e.stopImmediatePropagation();
}
//#endregion
//#region node_modules/d3-drag/src/nodrag.js
function Kt(e) {
	var t = e.document.documentElement, n = Bt(e).on("dragstart.drag", Gt, Ut);
	"onselectstart" in t ? n.on("selectstart.drag", Gt, Ut) : (t.__noselect = t.style.MozUserSelect, t.style.MozUserSelect = "none");
}
function qt(e, t) {
	var n = e.document.documentElement, r = Bt(e).on("dragstart.drag", null);
	t && (r.on("click.drag", Gt, Ut), setTimeout(function() {
		r.on("click.drag", null);
	}, 0)), "onselectstart" in n ? r.on("selectstart.drag", null) : (n.style.MozUserSelect = n.__noselect, delete n.__noselect);
}
//#endregion
//#region node_modules/d3-drag/src/constant.js
var Jt = (e) => () => e;
//#endregion
//#region node_modules/d3-drag/src/event.js
function Yt(e, { sourceEvent: t, subject: n, target: r, identifier: i, active: a, x: o, y: s, dx: c, dy: l, dispatch: u }) {
	Object.defineProperties(this, {
		type: {
			value: e,
			enumerable: !0,
			configurable: !0
		},
		sourceEvent: {
			value: t,
			enumerable: !0,
			configurable: !0
		},
		subject: {
			value: n,
			enumerable: !0,
			configurable: !0
		},
		target: {
			value: r,
			enumerable: !0,
			configurable: !0
		},
		identifier: {
			value: i,
			enumerable: !0,
			configurable: !0
		},
		active: {
			value: a,
			enumerable: !0,
			configurable: !0
		},
		x: {
			value: o,
			enumerable: !0,
			configurable: !0
		},
		y: {
			value: s,
			enumerable: !0,
			configurable: !0
		},
		dx: {
			value: c,
			enumerable: !0,
			configurable: !0
		},
		dy: {
			value: l,
			enumerable: !0,
			configurable: !0
		},
		_: { value: u }
	});
}
Yt.prototype.on = function() {
	var e = this._.on.apply(this._, arguments);
	return e === this._ ? this : e;
};
//#endregion
//#region node_modules/d3-drag/src/drag.js
function Xt(e) {
	return !e.ctrlKey && !e.button;
}
function Zt() {
	return this.parentNode;
}
function Qt(e, t) {
	return t ?? {
		x: e.x,
		y: e.y
	};
}
function $t() {
	return navigator.maxTouchPoints || "ontouchstart" in this;
}
function en() {
	var e = Xt, t = Zt, n = Qt, r = $t, i = {}, a = w("start", "drag", "end"), o = 0, s, c, l, u, d = 0;
	function f(e) {
		e.on("mousedown.drag", p).filter(r).on("touchstart.drag", g).on("touchmove.drag", _, Ht).on("touchend.drag touchcancel.drag", v).style("touch-action", "none").style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
	}
	function p(n, r) {
		if (!(u || !e.call(this, n, r))) {
			var i = y(this, t.call(this, n, r), n, r, "mouse");
			i && (Bt(n.view).on("mousemove.drag", m, Ut).on("mouseup.drag", h, Ut), Kt(n.view), Wt(n), l = !1, s = n.clientX, c = n.clientY, i("start", n));
		}
	}
	function m(e) {
		if (Gt(e), !l) {
			var t = e.clientX - s, n = e.clientY - c;
			l = t * t + n * n > d;
		}
		i.mouse("drag", e);
	}
	function h(e) {
		Bt(e.view).on("mousemove.drag mouseup.drag", null), qt(e.view, l), Gt(e), i.mouse("end", e);
	}
	function g(n, r) {
		if (e.call(this, n, r)) {
			var i = n.changedTouches, a = t.call(this, n, r), o = i.length, s, c;
			for (s = 0; s < o; ++s) (c = y(this, a, n, r, i[s].identifier, i[s])) && (Wt(n), c("start", n, i[s]));
		}
	}
	function _(e) {
		var t = e.changedTouches, n = t.length, r, a;
		for (r = 0; r < n; ++r) (a = i[t[r].identifier]) && (Gt(e), a("drag", e, t[r]));
	}
	function v(e) {
		var t = e.changedTouches, n = t.length, r, a;
		for (u && clearTimeout(u), u = setTimeout(function() {
			u = null;
		}, 500), r = 0; r < n; ++r) (a = i[t[r].identifier]) && (Wt(e), a("end", e, t[r]));
	}
	function y(e, t, r, s, c, l) {
		var u = a.copy(), d = Vt(l || r, t), p, m, h;
		if ((h = n.call(e, new Yt("beforestart", {
			sourceEvent: r,
			target: f,
			identifier: c,
			active: o,
			x: d[0],
			y: d[1],
			dx: 0,
			dy: 0,
			dispatch: u
		}), s)) != null) return p = h.x - d[0] || 0, m = h.y - d[1] || 0, function n(r, a, l) {
			var g = d, _;
			switch (r) {
				case "start":
					i[c] = n, _ = o++;
					break;
				case "end": delete i[c], --o;
				case "drag":
					d = Vt(l || a, t), _ = o;
					break;
			}
			u.call(r, e, new Yt(r, {
				sourceEvent: a,
				subject: h,
				target: f,
				identifier: c,
				active: _,
				x: d[0] + p,
				y: d[1] + m,
				dx: d[0] - g[0],
				dy: d[1] - g[1],
				dispatch: u
			}), s);
		};
	}
	return f.filter = function(t) {
		return arguments.length ? (e = typeof t == "function" ? t : Jt(!!t), f) : e;
	}, f.container = function(e) {
		return arguments.length ? (t = typeof e == "function" ? e : Jt(e), f) : t;
	}, f.subject = function(e) {
		return arguments.length ? (n = typeof e == "function" ? e : Jt(e), f) : n;
	}, f.touchable = function(e) {
		return arguments.length ? (r = typeof e == "function" ? e : Jt(!!e), f) : r;
	}, f.on = function() {
		var e = a.on.apply(a, arguments);
		return e === a ? f : e;
	}, f.clickDistance = function(e) {
		return arguments.length ? (d = (e = +e) * e, f) : Math.sqrt(d);
	}, f;
}
//#endregion
//#region node_modules/d3-color/src/define.js
function tn(e, t, n) {
	e.prototype = t.prototype = n, n.constructor = e;
}
function nn(e, t) {
	var n = Object.create(e.prototype);
	for (var r in t) n[r] = t[r];
	return n;
}
//#endregion
//#region node_modules/d3-color/src/color.js
function rn() {}
var an = .7, on = 1 / an, sn = "\\s*([+-]?\\d+)\\s*", cn = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)\\s*", ln = "\\s*([+-]?(?:\\d*\\.)?\\d+(?:[eE][+-]?\\d+)?)%\\s*", un = /^#([0-9a-f]{3,8})$/, dn = RegExp(`^rgb\\(${sn},${sn},${sn}\\)$`), fn = RegExp(`^rgb\\(${ln},${ln},${ln}\\)$`), pn = RegExp(`^rgba\\(${sn},${sn},${sn},${cn}\\)$`), mn = RegExp(`^rgba\\(${ln},${ln},${ln},${cn}\\)$`), hn = RegExp(`^hsl\\(${cn},${ln},${ln}\\)$`), gn = RegExp(`^hsla\\(${cn},${ln},${ln},${cn}\\)$`), _n = {
	aliceblue: 15792383,
	antiquewhite: 16444375,
	aqua: 65535,
	aquamarine: 8388564,
	azure: 15794175,
	beige: 16119260,
	bisque: 16770244,
	black: 0,
	blanchedalmond: 16772045,
	blue: 255,
	blueviolet: 9055202,
	brown: 10824234,
	burlywood: 14596231,
	cadetblue: 6266528,
	chartreuse: 8388352,
	chocolate: 13789470,
	coral: 16744272,
	cornflowerblue: 6591981,
	cornsilk: 16775388,
	crimson: 14423100,
	cyan: 65535,
	darkblue: 139,
	darkcyan: 35723,
	darkgoldenrod: 12092939,
	darkgray: 11119017,
	darkgreen: 25600,
	darkgrey: 11119017,
	darkkhaki: 12433259,
	darkmagenta: 9109643,
	darkolivegreen: 5597999,
	darkorange: 16747520,
	darkorchid: 10040012,
	darkred: 9109504,
	darksalmon: 15308410,
	darkseagreen: 9419919,
	darkslateblue: 4734347,
	darkslategray: 3100495,
	darkslategrey: 3100495,
	darkturquoise: 52945,
	darkviolet: 9699539,
	deeppink: 16716947,
	deepskyblue: 49151,
	dimgray: 6908265,
	dimgrey: 6908265,
	dodgerblue: 2003199,
	firebrick: 11674146,
	floralwhite: 16775920,
	forestgreen: 2263842,
	fuchsia: 16711935,
	gainsboro: 14474460,
	ghostwhite: 16316671,
	gold: 16766720,
	goldenrod: 14329120,
	gray: 8421504,
	green: 32768,
	greenyellow: 11403055,
	grey: 8421504,
	honeydew: 15794160,
	hotpink: 16738740,
	indianred: 13458524,
	indigo: 4915330,
	ivory: 16777200,
	khaki: 15787660,
	lavender: 15132410,
	lavenderblush: 16773365,
	lawngreen: 8190976,
	lemonchiffon: 16775885,
	lightblue: 11393254,
	lightcoral: 15761536,
	lightcyan: 14745599,
	lightgoldenrodyellow: 16448210,
	lightgray: 13882323,
	lightgreen: 9498256,
	lightgrey: 13882323,
	lightpink: 16758465,
	lightsalmon: 16752762,
	lightseagreen: 2142890,
	lightskyblue: 8900346,
	lightslategray: 7833753,
	lightslategrey: 7833753,
	lightsteelblue: 11584734,
	lightyellow: 16777184,
	lime: 65280,
	limegreen: 3329330,
	linen: 16445670,
	magenta: 16711935,
	maroon: 8388608,
	mediumaquamarine: 6737322,
	mediumblue: 205,
	mediumorchid: 12211667,
	mediumpurple: 9662683,
	mediumseagreen: 3978097,
	mediumslateblue: 8087790,
	mediumspringgreen: 64154,
	mediumturquoise: 4772300,
	mediumvioletred: 13047173,
	midnightblue: 1644912,
	mintcream: 16121850,
	mistyrose: 16770273,
	moccasin: 16770229,
	navajowhite: 16768685,
	navy: 128,
	oldlace: 16643558,
	olive: 8421376,
	olivedrab: 7048739,
	orange: 16753920,
	orangered: 16729344,
	orchid: 14315734,
	palegoldenrod: 15657130,
	palegreen: 10025880,
	paleturquoise: 11529966,
	palevioletred: 14381203,
	papayawhip: 16773077,
	peachpuff: 16767673,
	peru: 13468991,
	pink: 16761035,
	plum: 14524637,
	powderblue: 11591910,
	purple: 8388736,
	rebeccapurple: 6697881,
	red: 16711680,
	rosybrown: 12357519,
	royalblue: 4286945,
	saddlebrown: 9127187,
	salmon: 16416882,
	sandybrown: 16032864,
	seagreen: 3050327,
	seashell: 16774638,
	sienna: 10506797,
	silver: 12632256,
	skyblue: 8900331,
	slateblue: 6970061,
	slategray: 7372944,
	slategrey: 7372944,
	snow: 16775930,
	springgreen: 65407,
	steelblue: 4620980,
	tan: 13808780,
	teal: 32896,
	thistle: 14204888,
	tomato: 16737095,
	turquoise: 4251856,
	violet: 15631086,
	wheat: 16113331,
	white: 16777215,
	whitesmoke: 16119285,
	yellow: 16776960,
	yellowgreen: 10145074
};
tn(rn, Sn, {
	copy(e) {
		return Object.assign(new this.constructor(), this, e);
	},
	displayable() {
		return this.rgb().displayable();
	},
	hex: vn,
	formatHex: vn,
	formatHex8: yn,
	formatHsl: bn,
	formatRgb: xn,
	toString: xn
});
function vn() {
	return this.rgb().formatHex();
}
function yn() {
	return this.rgb().formatHex8();
}
function bn() {
	return Pn(this).formatHsl();
}
function xn() {
	return this.rgb().formatRgb();
}
function Sn(e) {
	var t, n;
	return e = (e + "").trim().toLowerCase(), (t = un.exec(e)) ? (n = t[1].length, t = parseInt(t[1], 16), n === 6 ? Cn(t) : n === 3 ? new H(t >> 8 & 15 | t >> 4 & 240, t >> 4 & 15 | t & 240, (t & 15) << 4 | t & 15, 1) : n === 8 ? wn(t >> 24 & 255, t >> 16 & 255, t >> 8 & 255, (t & 255) / 255) : n === 4 ? wn(t >> 12 & 15 | t >> 8 & 240, t >> 8 & 15 | t >> 4 & 240, t >> 4 & 15 | t & 240, ((t & 15) << 4 | t & 15) / 255) : null) : (t = dn.exec(e)) ? new H(t[1], t[2], t[3], 1) : (t = fn.exec(e)) ? new H(t[1] * 255 / 100, t[2] * 255 / 100, t[3] * 255 / 100, 1) : (t = pn.exec(e)) ? wn(t[1], t[2], t[3], t[4]) : (t = mn.exec(e)) ? wn(t[1] * 255 / 100, t[2] * 255 / 100, t[3] * 255 / 100, t[4]) : (t = hn.exec(e)) ? Nn(t[1], t[2] / 100, t[3] / 100, 1) : (t = gn.exec(e)) ? Nn(t[1], t[2] / 100, t[3] / 100, t[4]) : _n.hasOwnProperty(e) ? Cn(_n[e]) : e === "transparent" ? new H(NaN, NaN, NaN, 0) : null;
}
function Cn(e) {
	return new H(e >> 16 & 255, e >> 8 & 255, e & 255, 1);
}
function wn(e, t, n, r) {
	return r <= 0 && (e = t = n = NaN), new H(e, t, n, r);
}
function Tn(e) {
	return e instanceof rn || (e = Sn(e)), e ? (e = e.rgb(), new H(e.r, e.g, e.b, e.opacity)) : new H();
}
function En(e, t, n, r) {
	return arguments.length === 1 ? Tn(e) : new H(e, t, n, r ?? 1);
}
function H(e, t, n, r) {
	this.r = +e, this.g = +t, this.b = +n, this.opacity = +r;
}
tn(H, En, nn(rn, {
	brighter(e) {
		return e = e == null ? on : on ** +e, new H(this.r * e, this.g * e, this.b * e, this.opacity);
	},
	darker(e) {
		return e = e == null ? an : an ** +e, new H(this.r * e, this.g * e, this.b * e, this.opacity);
	},
	rgb() {
		return this;
	},
	clamp() {
		return new H(jn(this.r), jn(this.g), jn(this.b), An(this.opacity));
	},
	displayable() {
		return -.5 <= this.r && this.r < 255.5 && -.5 <= this.g && this.g < 255.5 && -.5 <= this.b && this.b < 255.5 && 0 <= this.opacity && this.opacity <= 1;
	},
	hex: Dn,
	formatHex: Dn,
	formatHex8: On,
	formatRgb: kn,
	toString: kn
}));
function Dn() {
	return `#${Mn(this.r)}${Mn(this.g)}${Mn(this.b)}`;
}
function On() {
	return `#${Mn(this.r)}${Mn(this.g)}${Mn(this.b)}${Mn((isNaN(this.opacity) ? 1 : this.opacity) * 255)}`;
}
function kn() {
	let e = An(this.opacity);
	return `${e === 1 ? "rgb(" : "rgba("}${jn(this.r)}, ${jn(this.g)}, ${jn(this.b)}${e === 1 ? ")" : `, ${e})`}`;
}
function An(e) {
	return isNaN(e) ? 1 : Math.max(0, Math.min(1, e));
}
function jn(e) {
	return Math.max(0, Math.min(255, Math.round(e) || 0));
}
function Mn(e) {
	return e = jn(e), (e < 16 ? "0" : "") + e.toString(16);
}
function Nn(e, t, n, r) {
	return r <= 0 ? e = t = n = NaN : n <= 0 || n >= 1 ? e = t = NaN : t <= 0 && (e = NaN), new In(e, t, n, r);
}
function Pn(e) {
	if (e instanceof In) return new In(e.h, e.s, e.l, e.opacity);
	if (e instanceof rn || (e = Sn(e)), !e) return new In();
	if (e instanceof In) return e;
	e = e.rgb();
	var t = e.r / 255, n = e.g / 255, r = e.b / 255, i = Math.min(t, n, r), a = Math.max(t, n, r), o = NaN, s = a - i, c = (a + i) / 2;
	return s ? (o = t === a ? (n - r) / s + (n < r) * 6 : n === a ? (r - t) / s + 2 : (t - n) / s + 4, s /= c < .5 ? a + i : 2 - a - i, o *= 60) : s = c > 0 && c < 1 ? 0 : o, new In(o, s, c, e.opacity);
}
function Fn(e, t, n, r) {
	return arguments.length === 1 ? Pn(e) : new In(e, t, n, r ?? 1);
}
function In(e, t, n, r) {
	this.h = +e, this.s = +t, this.l = +n, this.opacity = +r;
}
tn(In, Fn, nn(rn, {
	brighter(e) {
		return e = e == null ? on : on ** +e, new In(this.h, this.s, this.l * e, this.opacity);
	},
	darker(e) {
		return e = e == null ? an : an ** +e, new In(this.h, this.s, this.l * e, this.opacity);
	},
	rgb() {
		var e = this.h % 360 + (this.h < 0) * 360, t = isNaN(e) || isNaN(this.s) ? 0 : this.s, n = this.l, r = n + (n < .5 ? n : 1 - n) * t, i = 2 * n - r;
		return new H(zn(e >= 240 ? e - 240 : e + 120, i, r), zn(e, i, r), zn(e < 120 ? e + 240 : e - 120, i, r), this.opacity);
	},
	clamp() {
		return new In(Ln(this.h), Rn(this.s), Rn(this.l), An(this.opacity));
	},
	displayable() {
		return (0 <= this.s && this.s <= 1 || isNaN(this.s)) && 0 <= this.l && this.l <= 1 && 0 <= this.opacity && this.opacity <= 1;
	},
	formatHsl() {
		let e = An(this.opacity);
		return `${e === 1 ? "hsl(" : "hsla("}${Ln(this.h)}, ${Rn(this.s) * 100}%, ${Rn(this.l) * 100}%${e === 1 ? ")" : `, ${e})`}`;
	}
}));
function Ln(e) {
	return e = (e || 0) % 360, e < 0 ? e + 360 : e;
}
function Rn(e) {
	return Math.max(0, Math.min(1, e || 0));
}
function zn(e, t, n) {
	return (e < 60 ? t + (n - t) * e / 60 : e < 180 ? n : e < 240 ? t + (n - t) * (240 - e) / 60 : t) * 255;
}
//#endregion
//#region node_modules/d3-interpolate/src/constant.js
var Bn = (e) => () => e;
//#endregion
//#region node_modules/d3-interpolate/src/color.js
function Vn(e, t) {
	return function(n) {
		return e + n * t;
	};
}
function Hn(e, t, n) {
	return e **= +n, t = t ** +n - e, n = 1 / n, function(r) {
		return (e + r * t) ** +n;
	};
}
function Un(e) {
	return (e = +e) == 1 ? Wn : function(t, n) {
		return n - t ? Hn(t, n, e) : Bn(isNaN(t) ? n : t);
	};
}
function Wn(e, t) {
	var n = t - e;
	return n ? Vn(e, n) : Bn(isNaN(e) ? t : e);
}
//#endregion
//#region node_modules/d3-interpolate/src/rgb.js
var Gn = (function e(t) {
	var n = Un(t);
	function r(e, t) {
		var r = n((e = En(e)).r, (t = En(t)).r), i = n(e.g, t.g), a = n(e.b, t.b), o = Wn(e.opacity, t.opacity);
		return function(t) {
			return e.r = r(t), e.g = i(t), e.b = a(t), e.opacity = o(t), e + "";
		};
	}
	return r.gamma = e, r;
})(1);
//#endregion
//#region node_modules/d3-interpolate/src/numberArray.js
function Kn(e, t) {
	t ||= [];
	var n = e ? Math.min(t.length, e.length) : 0, r = t.slice(), i;
	return function(a) {
		for (i = 0; i < n; ++i) r[i] = e[i] * (1 - a) + t[i] * a;
		return r;
	};
}
function qn(e) {
	return ArrayBuffer.isView(e) && !(e instanceof DataView);
}
//#endregion
//#region node_modules/d3-interpolate/src/array.js
function Jn(e, t) {
	var n = t ? t.length : 0, r = e ? Math.min(n, e.length) : 0, i = Array(r), a = Array(n), o;
	for (o = 0; o < r; ++o) i[o] = rr(e[o], t[o]);
	for (; o < n; ++o) a[o] = t[o];
	return function(e) {
		for (o = 0; o < r; ++o) a[o] = i[o](e);
		return a;
	};
}
//#endregion
//#region node_modules/d3-interpolate/src/date.js
function Yn(e, t) {
	var n = /* @__PURE__ */ new Date();
	return e = +e, t = +t, function(r) {
		return n.setTime(e * (1 - r) + t * r), n;
	};
}
//#endregion
//#region node_modules/d3-interpolate/src/number.js
function Xn(e, t) {
	return e = +e, t = +t, function(n) {
		return e * (1 - n) + t * n;
	};
}
//#endregion
//#region node_modules/d3-interpolate/src/object.js
function Zn(e, t) {
	var n = {}, r = {}, i;
	for (i in (typeof e != "object" || !e) && (e = {}), (typeof t != "object" || !t) && (t = {}), t) i in e ? n[i] = rr(e[i], t[i]) : r[i] = t[i];
	return function(e) {
		for (i in n) r[i] = n[i](e);
		return r;
	};
}
//#endregion
//#region node_modules/d3-interpolate/src/string.js
var Qn = /[-+]?(?:\d+\.?\d*|\.?\d+)(?:[eE][-+]?\d+)?/g, $n = new RegExp(Qn.source, "g");
function er(e) {
	return function() {
		return e;
	};
}
function tr(e) {
	return function(t) {
		return e(t) + "";
	};
}
function nr(e, t) {
	var n = Qn.lastIndex = $n.lastIndex = 0, r, i, a, o = -1, s = [], c = [];
	for (e += "", t += ""; (r = Qn.exec(e)) && (i = $n.exec(t));) (a = i.index) > n && (a = t.slice(n, a), s[o] ? s[o] += a : s[++o] = a), (r = r[0]) === (i = i[0]) ? s[o] ? s[o] += i : s[++o] = i : (s[++o] = null, c.push({
		i: o,
		x: Xn(r, i)
	})), n = $n.lastIndex;
	return n < t.length && (a = t.slice(n), s[o] ? s[o] += a : s[++o] = a), s.length < 2 ? c[0] ? tr(c[0].x) : er(t) : (t = c.length, function(e) {
		for (var n = 0, r; n < t; ++n) s[(r = c[n]).i] = r.x(e);
		return s.join("");
	});
}
//#endregion
//#region node_modules/d3-interpolate/src/value.js
function rr(e, t) {
	var n = typeof t, r;
	return t == null || n === "boolean" ? Bn(t) : (n === "number" ? Xn : n === "string" ? (r = Sn(t)) ? (t = r, Gn) : nr : t instanceof Sn ? Gn : t instanceof Date ? Yn : qn(t) ? Kn : Array.isArray(t) ? Jn : typeof t.valueOf != "function" && typeof t.toString != "function" || isNaN(t) ? Zn : Xn)(e, t);
}
//#endregion
//#region node_modules/d3-interpolate/src/transform/decompose.js
var ir = 180 / Math.PI, ar = {
	translateX: 0,
	translateY: 0,
	rotate: 0,
	skewX: 0,
	scaleX: 1,
	scaleY: 1
};
function or(e, t, n, r, i, a) {
	var o, s, c;
	return (o = Math.sqrt(e * e + t * t)) && (e /= o, t /= o), (c = e * n + t * r) && (n -= e * c, r -= t * c), (s = Math.sqrt(n * n + r * r)) && (n /= s, r /= s, c /= s), e * r < t * n && (e = -e, t = -t, c = -c, o = -o), {
		translateX: i,
		translateY: a,
		rotate: Math.atan2(t, e) * ir,
		skewX: Math.atan(c) * ir,
		scaleX: o,
		scaleY: s
	};
}
//#endregion
//#region node_modules/d3-interpolate/src/transform/parse.js
var sr;
function cr(e) {
	let t = new (typeof DOMMatrix == "function" ? DOMMatrix : WebKitCSSMatrix)(e + "");
	return t.isIdentity ? ar : or(t.a, t.b, t.c, t.d, t.e, t.f);
}
function lr(e) {
	return e == null || (sr ||= document.createElementNS("http://www.w3.org/2000/svg", "g"), sr.setAttribute("transform", e), !(e = sr.transform.baseVal.consolidate())) ? ar : (e = e.matrix, or(e.a, e.b, e.c, e.d, e.e, e.f));
}
//#endregion
//#region node_modules/d3-interpolate/src/transform/index.js
function ur(e, t, n, r) {
	function i(e) {
		return e.length ? e.pop() + " " : "";
	}
	function a(e, r, i, a, o, s) {
		if (e !== i || r !== a) {
			var c = o.push("translate(", null, t, null, n);
			s.push({
				i: c - 4,
				x: Xn(e, i)
			}, {
				i: c - 2,
				x: Xn(r, a)
			});
		} else (i || a) && o.push("translate(" + i + t + a + n);
	}
	function o(e, t, n, a) {
		e === t ? t && n.push(i(n) + "rotate(" + t + r) : (e - t > 180 ? t += 360 : t - e > 180 && (e += 360), a.push({
			i: n.push(i(n) + "rotate(", null, r) - 2,
			x: Xn(e, t)
		}));
	}
	function s(e, t, n, a) {
		e === t ? t && n.push(i(n) + "skewX(" + t + r) : a.push({
			i: n.push(i(n) + "skewX(", null, r) - 2,
			x: Xn(e, t)
		});
	}
	function c(e, t, n, r, a, o) {
		if (e !== n || t !== r) {
			var s = a.push(i(a) + "scale(", null, ",", null, ")");
			o.push({
				i: s - 4,
				x: Xn(e, n)
			}, {
				i: s - 2,
				x: Xn(t, r)
			});
		} else (n !== 1 || r !== 1) && a.push(i(a) + "scale(" + n + "," + r + ")");
	}
	return function(t, n) {
		var r = [], i = [];
		return t = e(t), n = e(n), a(t.translateX, t.translateY, n.translateX, n.translateY, r, i), o(t.rotate, n.rotate, r, i), s(t.skewX, n.skewX, r, i), c(t.scaleX, t.scaleY, n.scaleX, n.scaleY, r, i), t = n = null, function(e) {
			for (var t = -1, n = i.length, a; ++t < n;) r[(a = i[t]).i] = a.x(e);
			return r.join("");
		};
	};
}
var dr = ur(cr, "px, ", "px)", "deg)"), fr = ur(lr, ", ", ")", ")"), pr = 1e-12;
function mr(e) {
	return ((e = Math.exp(e)) + 1 / e) / 2;
}
function hr(e) {
	return ((e = Math.exp(e)) - 1 / e) / 2;
}
function gr(e) {
	return ((e = Math.exp(2 * e)) - 1) / (e + 1);
}
var _r = (function e(t, n, r) {
	function i(e, i) {
		var a = e[0], o = e[1], s = e[2], c = i[0], l = i[1], u = i[2], d = c - a, f = l - o, p = d * d + f * f, m, h;
		if (p < pr) h = Math.log(u / s) / t, m = function(e) {
			return [
				a + e * d,
				o + e * f,
				s * Math.exp(t * e * h)
			];
		};
		else {
			var g = Math.sqrt(p), _ = (u * u - s * s + r * p) / (2 * s * n * g), v = (u * u - s * s - r * p) / (2 * u * n * g), y = Math.log(Math.sqrt(_ * _ + 1) - _);
			h = (Math.log(Math.sqrt(v * v + 1) - v) - y) / t, m = function(e) {
				var r = e * h, i = mr(y), c = s / (n * g) * (i * gr(t * r + y) - hr(y));
				return [
					a + c * d,
					o + c * f,
					s * i / mr(t * r + y)
				];
			};
		}
		return m.duration = h * 1e3 * t / Math.SQRT2, m;
	}
	return i.rho = function(t) {
		var n = Math.max(.001, +t), r = n * n;
		return e(n, r, r * r);
	}, i;
})(Math.SQRT2, 2, 4), vr = 0, yr = 0, br = 0, xr = 1e3, Sr, Cr, wr = 0, Tr = 0, Er = 0, Dr = typeof performance == "object" && performance.now ? performance : Date, Or = typeof window == "object" && window.requestAnimationFrame ? window.requestAnimationFrame.bind(window) : function(e) {
	setTimeout(e, 17);
};
function kr() {
	return Tr ||= (Or(Ar), Dr.now() + Er);
}
function Ar() {
	Tr = 0;
}
function jr() {
	this._call = this._time = this._next = null;
}
jr.prototype = Mr.prototype = {
	constructor: jr,
	restart: function(e, t, n) {
		if (typeof e != "function") throw TypeError("callback is not a function");
		n = (n == null ? kr() : +n) + (t == null ? 0 : +t), !this._next && Cr !== this && (Cr ? Cr._next = this : Sr = this, Cr = this), this._call = e, this._time = n, Lr();
	},
	stop: function() {
		this._call && (this._call = null, this._time = Infinity, Lr());
	}
};
function Mr(e, t, n) {
	var r = new jr();
	return r.restart(e, t, n), r;
}
function Nr() {
	kr(), ++vr;
	for (var e = Sr, t; e;) (t = Tr - e._time) >= 0 && e._call.call(void 0, t), e = e._next;
	--vr;
}
function Pr() {
	Tr = (wr = Dr.now()) + Er, vr = yr = 0;
	try {
		Nr();
	} finally {
		vr = 0, Ir(), Tr = 0;
	}
}
function Fr() {
	var e = Dr.now(), t = e - wr;
	t > xr && (Er -= t, wr = e);
}
function Ir() {
	for (var e, t = Sr, n, r = Infinity; t;) t._call ? (r > t._time && (r = t._time), e = t, t = t._next) : (n = t._next, t._next = null, t = e ? e._next = n : Sr = n);
	Cr = e, Lr(r);
}
function Lr(e) {
	vr || (yr &&= clearTimeout(yr), e - Tr > 24 ? (e < Infinity && (yr = setTimeout(Pr, e - Dr.now() - Er)), br &&= clearInterval(br)) : (br ||= (wr = Dr.now(), setInterval(Fr, xr)), vr = 1, Or(Pr)));
}
//#endregion
//#region node_modules/d3-timer/src/timeout.js
function Rr(e, t, n) {
	var r = new jr();
	return t = t == null ? 0 : +t, r.restart((n) => {
		r.stop(), e(n + t);
	}, t, n), r;
}
//#endregion
//#region node_modules/d3-transition/src/transition/schedule.js
var zr = w("start", "end", "cancel", "interrupt"), Br = [];
function Vr(e, t, n, r, i, a) {
	var o = e.__transition;
	if (!o) e.__transition = {};
	else if (n in o) return;
	Gr(e, n, {
		name: t,
		index: r,
		group: i,
		on: zr,
		tween: Br,
		time: a.time,
		delay: a.delay,
		duration: a.duration,
		ease: a.ease,
		timer: null,
		state: 0
	});
}
function Hr(e, t) {
	var n = Wr(e, t);
	if (n.state > 0) throw Error("too late; already scheduled");
	return n;
}
function Ur(e, t) {
	var n = Wr(e, t);
	if (n.state > 3) throw Error("too late; already running");
	return n;
}
function Wr(e, t) {
	var n = e.__transition;
	if (!n || !(n = n[t])) throw Error("transition not found");
	return n;
}
function Gr(e, t, n) {
	var r = e.__transition, i;
	r[t] = n, n.timer = Mr(a, 0, n.time);
	function a(e) {
		n.state = 1, n.timer.restart(o, n.delay, n.time), n.delay <= e && o(e - n.delay);
	}
	function o(a) {
		var l, u, d, f;
		if (n.state !== 1) return c();
		for (l in r) if (f = r[l], f.name === n.name) {
			if (f.state === 3) return Rr(o);
			f.state === 4 ? (f.state = 6, f.timer.stop(), f.on.call("interrupt", e, e.__data__, f.index, f.group), delete r[l]) : +l < t && (f.state = 6, f.timer.stop(), f.on.call("cancel", e, e.__data__, f.index, f.group), delete r[l]);
		}
		if (Rr(function() {
			n.state === 3 && (n.state = 4, n.timer.restart(s, n.delay, n.time), s(a));
		}), n.state = 2, n.on.call("start", e, e.__data__, n.index, n.group), n.state === 2) {
			for (n.state = 3, i = Array(d = n.tween.length), l = 0, u = -1; l < d; ++l) (f = n.tween[l].value.call(e, e.__data__, n.index, n.group)) && (i[++u] = f);
			i.length = u + 1;
		}
	}
	function s(t) {
		for (var r = t < n.duration ? n.ease.call(null, t / n.duration) : (n.timer.restart(c), n.state = 5, 1), a = -1, o = i.length; ++a < o;) i[a].call(e, r);
		n.state === 5 && (n.on.call("end", e, e.__data__, n.index, n.group), c());
	}
	function c() {
		for (var i in n.state = 6, n.timer.stop(), delete r[t], r) return;
		delete e.__transition;
	}
}
//#endregion
//#region node_modules/d3-transition/src/interrupt.js
function Kr(e, t) {
	var n = e.__transition, r, i, a = !0, o;
	if (n) {
		for (o in t = t == null ? null : t + "", n) {
			if ((r = n[o]).name !== t) {
				a = !1;
				continue;
			}
			i = r.state > 2 && r.state < 5, r.state = 6, r.timer.stop(), r.on.call(i ? "interrupt" : "cancel", e, e.__data__, r.index, r.group), delete n[o];
		}
		a && delete e.__transition;
	}
}
//#endregion
//#region node_modules/d3-transition/src/selection/interrupt.js
function qr(e) {
	return this.each(function() {
		Kr(this, e);
	});
}
//#endregion
//#region node_modules/d3-transition/src/transition/tween.js
function Jr(e, t) {
	var n, r;
	return function() {
		var i = Ur(this, e), a = i.tween;
		if (a !== n) {
			r = n = a;
			for (var o = 0, s = r.length; o < s; ++o) if (r[o].name === t) {
				r = r.slice(), r.splice(o, 1);
				break;
			}
		}
		i.tween = r;
	};
}
function Yr(e, t, n) {
	var r, i;
	if (typeof n != "function") throw Error();
	return function() {
		var a = Ur(this, e), o = a.tween;
		if (o !== r) {
			i = (r = o).slice();
			for (var s = {
				name: t,
				value: n
			}, c = 0, l = i.length; c < l; ++c) if (i[c].name === t) {
				i[c] = s;
				break;
			}
			c === l && i.push(s);
		}
		a.tween = i;
	};
}
function Xr(e, t) {
	var n = this._id;
	if (e += "", arguments.length < 2) {
		for (var r = Wr(this.node(), n).tween, i = 0, a = r.length, o; i < a; ++i) if ((o = r[i]).name === e) return o.value;
		return null;
	}
	return this.each((t == null ? Jr : Yr)(n, e, t));
}
function Zr(e, t, n) {
	var r = e._id;
	return e.each(function() {
		var e = Ur(this, r);
		(e.value ||= {})[t] = n.apply(this, arguments);
	}), function(e) {
		return Wr(e, r).value[t];
	};
}
//#endregion
//#region node_modules/d3-transition/src/transition/interpolate.js
function Qr(e, t) {
	var n;
	return (typeof t == "number" ? Xn : t instanceof Sn ? Gn : (n = Sn(t)) ? (t = n, Gn) : nr)(e, t);
}
//#endregion
//#region node_modules/d3-transition/src/transition/attr.js
function $r(e) {
	return function() {
		this.removeAttribute(e);
	};
}
function ei(e) {
	return function() {
		this.removeAttributeNS(e.space, e.local);
	};
}
function ti(e, t, n) {
	var r, i = n + "", a;
	return function() {
		var o = this.getAttribute(e);
		return o === i ? null : o === r ? a : a = t(r = o, n);
	};
}
function ni(e, t, n) {
	var r, i = n + "", a;
	return function() {
		var o = this.getAttributeNS(e.space, e.local);
		return o === i ? null : o === r ? a : a = t(r = o, n);
	};
}
function ri(e, t, n) {
	var r, i, a;
	return function() {
		var o, s = n(this), c;
		return s == null ? void this.removeAttribute(e) : (o = this.getAttribute(e), c = s + "", o === c ? null : o === r && c === i ? a : (i = c, a = t(r = o, s)));
	};
}
function ii(e, t, n) {
	var r, i, a;
	return function() {
		var o, s = n(this), c;
		return s == null ? void this.removeAttributeNS(e.space, e.local) : (o = this.getAttributeNS(e.space, e.local), c = s + "", o === c ? null : o === r && c === i ? a : (i = c, a = t(r = o, s)));
	};
}
function ai(e, t) {
	var n = A(e), r = n === "transform" ? fr : Qr;
	return this.attrTween(e, typeof t == "function" ? (n.local ? ii : ri)(n, r, Zr(this, "attr." + e, t)) : t == null ? (n.local ? ei : $r)(n) : (n.local ? ni : ti)(n, r, t));
}
//#endregion
//#region node_modules/d3-transition/src/transition/attrTween.js
function U(e, t) {
	return function(n) {
		this.setAttribute(e, t.call(this, n));
	};
}
function oi(e, t) {
	return function(n) {
		this.setAttributeNS(e.space, e.local, t.call(this, n));
	};
}
function si(e, t) {
	var n, r;
	function i() {
		var i = t.apply(this, arguments);
		return i !== r && (n = (r = i) && oi(e, i)), n;
	}
	return i._value = t, i;
}
function ci(e, t) {
	var n, r;
	function i() {
		var i = t.apply(this, arguments);
		return i !== r && (n = (r = i) && U(e, i)), n;
	}
	return i._value = t, i;
}
function li(e, t) {
	var n = "attr." + e;
	if (arguments.length < 2) return (n = this.tween(n)) && n._value;
	if (t == null) return this.tween(n, null);
	if (typeof t != "function") throw Error();
	var r = A(e);
	return this.tween(n, (r.local ? si : ci)(r, t));
}
//#endregion
//#region node_modules/d3-transition/src/transition/delay.js
function ui(e, t) {
	return function() {
		Hr(this, e).delay = +t.apply(this, arguments);
	};
}
function di(e, t) {
	return t = +t, function() {
		Hr(this, e).delay = t;
	};
}
function fi(e) {
	var t = this._id;
	return arguments.length ? this.each((typeof e == "function" ? ui : di)(t, e)) : Wr(this.node(), t).delay;
}
//#endregion
//#region node_modules/d3-transition/src/transition/duration.js
function pi(e, t) {
	return function() {
		Ur(this, e).duration = +t.apply(this, arguments);
	};
}
function mi(e, t) {
	return t = +t, function() {
		Ur(this, e).duration = t;
	};
}
function hi(e) {
	var t = this._id;
	return arguments.length ? this.each((typeof e == "function" ? pi : mi)(t, e)) : Wr(this.node(), t).duration;
}
//#endregion
//#region node_modules/d3-transition/src/transition/ease.js
function gi(e, t) {
	if (typeof t != "function") throw Error();
	return function() {
		Ur(this, e).ease = t;
	};
}
function _i(e) {
	var t = this._id;
	return arguments.length ? this.each(gi(t, e)) : Wr(this.node(), t).ease;
}
//#endregion
//#region node_modules/d3-transition/src/transition/easeVarying.js
function vi(e, t) {
	return function() {
		var n = t.apply(this, arguments);
		if (typeof n != "function") throw Error();
		Ur(this, e).ease = n;
	};
}
function yi(e) {
	if (typeof e != "function") throw Error();
	return this.each(vi(this._id, e));
}
//#endregion
//#region node_modules/d3-transition/src/transition/filter.js
function bi(e) {
	typeof e != "function" && (e = te(e));
	for (var t = this._groups, n = t.length, r = Array(n), i = 0; i < n; ++i) for (var a = t[i], o = a.length, s = r[i] = [], c, l = 0; l < o; ++l) (c = a[l]) && e.call(c, c.__data__, l, a) && s.push(c);
	return new qi(r, this._parents, this._name, this._id);
}
//#endregion
//#region node_modules/d3-transition/src/transition/merge.js
function xi(e) {
	if (e._id !== this._id) throw Error();
	for (var t = this._groups, n = e._groups, r = t.length, i = n.length, a = Math.min(r, i), o = Array(r), s = 0; s < a; ++s) for (var c = t[s], l = n[s], u = c.length, d = o[s] = Array(u), f, p = 0; p < u; ++p) (f = c[p] || l[p]) && (d[p] = f);
	for (; s < r; ++s) o[s] = t[s];
	return new qi(o, this._parents, this._name, this._id);
}
//#endregion
//#region node_modules/d3-transition/src/transition/on.js
function Si(e) {
	return (e + "").trim().split(/^|\s+/).every(function(e) {
		var t = e.indexOf(".");
		return t >= 0 && (e = e.slice(0, t)), !e || e === "start";
	});
}
function Ci(e, t, n) {
	var r, i, a = Si(t) ? Hr : Ur;
	return function() {
		var o = a(this, e), s = o.on;
		s !== r && (i = (r = s).copy()).on(t, n), o.on = i;
	};
}
function wi(e, t) {
	var n = this._id;
	return arguments.length < 2 ? Wr(this.node(), n).on.on(e) : this.each(Ci(n, e, t));
}
//#endregion
//#region node_modules/d3-transition/src/transition/remove.js
function Ti(e) {
	return function() {
		var t = this.parentNode;
		for (var n in this.__transition) if (+n !== e) return;
		t && t.removeChild(this);
	};
}
function Ei() {
	return this.on("end.remove", Ti(this._id));
}
//#endregion
//#region node_modules/d3-transition/src/transition/select.js
function Di(e) {
	var t = this._name, n = this._id;
	typeof e != "function" && (e = F(e));
	for (var r = this._groups, i = r.length, a = Array(i), o = 0; o < i; ++o) for (var s = r[o], c = s.length, l = a[o] = Array(c), u, d, f = 0; f < c; ++f) (u = s[f]) && (d = e.call(u, u.__data__, f, s)) && ("__data__" in u && (d.__data__ = u.__data__), l[f] = d, Vr(l[f], t, n, f, l, Wr(u, n)));
	return new qi(a, this._parents, t, n);
}
//#endregion
//#region node_modules/d3-transition/src/transition/selectAll.js
function Oi(e) {
	var t = this._name, n = this._id;
	typeof e != "function" && (e = R(e));
	for (var r = this._groups, i = r.length, a = [], o = [], s = 0; s < i; ++s) for (var c = r[s], l = c.length, u, d = 0; d < l; ++d) if (u = c[d]) {
		for (var f = e.call(u, u.__data__, d, c), p, m = Wr(u, n), h = 0, g = f.length; h < g; ++h) (p = f[h]) && Vr(p, t, n, h, f, m);
		a.push(f), o.push(u);
	}
	return new qi(a, o, t, n);
}
//#endregion
//#region node_modules/d3-transition/src/transition/selection.js
var ki = Rt.prototype.constructor;
function Ai() {
	return new ki(this._groups, this._parents);
}
//#endregion
//#region node_modules/d3-transition/src/transition/style.js
function ji(e, t) {
	var n, r, i;
	return function() {
		var a = Ge(this, e), o = (this.style.removeProperty(e), Ge(this, e));
		return a === o ? null : a === n && o === r ? i : i = t(n = a, r = o);
	};
}
function Mi(e) {
	return function() {
		this.style.removeProperty(e);
	};
}
function Ni(e, t, n) {
	var r, i = n + "", a;
	return function() {
		var o = Ge(this, e);
		return o === i ? null : o === r ? a : a = t(r = o, n);
	};
}
function Pi(e, t, n) {
	var r, i, a;
	return function() {
		var o = Ge(this, e), s = n(this), c = s + "";
		return s ?? (c = s = (this.style.removeProperty(e), Ge(this, e))), o === c ? null : o === r && c === i ? a : (i = c, a = t(r = o, s));
	};
}
function Fi(e, t) {
	var n, r, i, a = "style." + t, o = "end." + a, s;
	return function() {
		var c = Ur(this, e), l = c.on, u = c.value[a] == null ? s ||= Mi(t) : void 0;
		(l !== n || i !== u) && (r = (n = l).copy()).on(o, i = u), c.on = r;
	};
}
function Ii(e, t, n) {
	var r = (e += "") == "transform" ? dr : Qr;
	return t == null ? this.styleTween(e, ji(e, r)).on("end.style." + e, Mi(e)) : typeof t == "function" ? this.styleTween(e, Pi(e, r, Zr(this, "style." + e, t))).each(Fi(this._id, e)) : this.styleTween(e, Ni(e, r, t), n).on("end.style." + e, null);
}
//#endregion
//#region node_modules/d3-transition/src/transition/styleTween.js
function Li(e, t, n) {
	return function(r) {
		this.style.setProperty(e, t.call(this, r), n);
	};
}
function Ri(e, t, n) {
	var r, i;
	function a() {
		var a = t.apply(this, arguments);
		return a !== i && (r = (i = a) && Li(e, a, n)), r;
	}
	return a._value = t, a;
}
function zi(e, t, n) {
	var r = "style." + (e += "");
	if (arguments.length < 2) return (r = this.tween(r)) && r._value;
	if (t == null) return this.tween(r, null);
	if (typeof t != "function") throw Error();
	return this.tween(r, Ri(e, t, n ?? ""));
}
//#endregion
//#region node_modules/d3-transition/src/transition/text.js
function Bi(e) {
	return function() {
		this.textContent = e;
	};
}
function Vi(e) {
	return function() {
		var t = e(this);
		this.textContent = t ?? "";
	};
}
function Hi(e) {
	return this.tween("text", typeof e == "function" ? Vi(Zr(this, "text", e)) : Bi(e == null ? "" : e + ""));
}
//#endregion
//#region node_modules/d3-transition/src/transition/textTween.js
function Ui(e) {
	return function(t) {
		this.textContent = e.call(this, t);
	};
}
function Wi(e) {
	var t, n;
	function r() {
		var r = e.apply(this, arguments);
		return r !== n && (t = (n = r) && Ui(r)), t;
	}
	return r._value = e, r;
}
function W(e) {
	var t = "text";
	if (arguments.length < 1) return (t = this.tween(t)) && t._value;
	if (e == null) return this.tween(t, null);
	if (typeof e != "function") throw Error();
	return this.tween(t, Wi(e));
}
//#endregion
//#region node_modules/d3-transition/src/transition/transition.js
function G() {
	for (var e = this._name, t = this._id, n = Yi(), r = this._groups, i = r.length, a = 0; a < i; ++a) for (var o = r[a], s = o.length, c, l = 0; l < s; ++l) if (c = o[l]) {
		var u = Wr(c, t);
		Vr(c, e, n, l, o, {
			time: u.time + u.delay + u.duration,
			delay: 0,
			duration: u.duration,
			ease: u.ease
		});
	}
	return new qi(r, this._parents, e, n);
}
//#endregion
//#region node_modules/d3-transition/src/transition/end.js
function Gi() {
	var e, t, n = this, r = n._id, i = n.size();
	return new Promise(function(a, o) {
		var s = { value: o }, c = { value: function() {
			--i === 0 && a();
		} };
		n.each(function() {
			var n = Ur(this, r), i = n.on;
			i !== e && (t = (e = i).copy(), t._.cancel.push(s), t._.interrupt.push(s), t._.end.push(c)), n.on = t;
		}), i === 0 && a();
	});
}
//#endregion
//#region node_modules/d3-transition/src/transition/index.js
var Ki = 0;
function qi(e, t, n, r) {
	this._groups = e, this._parents = t, this._name = n, this._id = r;
}
function Ji(e) {
	return Rt().transition(e);
}
function Yi() {
	return ++Ki;
}
var Xi = Rt.prototype;
qi.prototype = Ji.prototype = {
	constructor: qi,
	select: Di,
	selectAll: Oi,
	selectChild: Xi.selectChild,
	selectChildren: Xi.selectChildren,
	filter: bi,
	merge: xi,
	selection: Ai,
	transition: G,
	call: Xi.call,
	nodes: Xi.nodes,
	node: Xi.node,
	size: Xi.size,
	empty: Xi.empty,
	each: Xi.each,
	on: wi,
	attr: ai,
	attrTween: li,
	style: Ii,
	styleTween: zi,
	text: Hi,
	textTween: W,
	remove: Ei,
	tween: Xr,
	delay: fi,
	duration: hi,
	ease: _i,
	easeVarying: yi,
	end: Gi,
	[Symbol.iterator]: Xi[Symbol.iterator]
};
//#endregion
//#region node_modules/d3-ease/src/cubic.js
function Zi(e) {
	return ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2;
}
//#endregion
//#region node_modules/d3-transition/src/selection/transition.js
var Qi = {
	time: null,
	delay: 0,
	duration: 250,
	ease: Zi
};
function $i(e, t) {
	for (var n; !(n = e.__transition) || !(n = n[t]);) if (!(e = e.parentNode)) throw Error(`transition ${t} not found`);
	return n;
}
function ea(e) {
	var t, n;
	e instanceof qi ? (t = e._id, e = e._name) : (t = Yi(), (n = Qi).time = kr(), e = e == null ? null : e + "");
	for (var r = this._groups, i = r.length, a = 0; a < i; ++a) for (var o = r[a], s = o.length, c, l = 0; l < s; ++l) (c = o[l]) && Vr(c, e, t, l, o, n || $i(c, t));
	return new qi(r, this._parents, e, t);
}
Rt.prototype.interrupt = qr, Rt.prototype.transition = ea;
//#endregion
//#region node_modules/d3-zoom/src/constant.js
var ta = (e) => () => e;
//#endregion
//#region node_modules/d3-zoom/src/event.js
function na(e, { sourceEvent: t, target: n, transform: r, dispatch: i }) {
	Object.defineProperties(this, {
		type: {
			value: e,
			enumerable: !0,
			configurable: !0
		},
		sourceEvent: {
			value: t,
			enumerable: !0,
			configurable: !0
		},
		target: {
			value: n,
			enumerable: !0,
			configurable: !0
		},
		transform: {
			value: r,
			enumerable: !0,
			configurable: !0
		},
		_: { value: i }
	});
}
//#endregion
//#region node_modules/d3-zoom/src/transform.js
function ra(e, t, n) {
	this.k = e, this.x = t, this.y = n;
}
ra.prototype = {
	constructor: ra,
	scale: function(e) {
		return e === 1 ? this : new ra(this.k * e, this.x, this.y);
	},
	translate: function(e, t) {
		return e === 0 & t === 0 ? this : new ra(this.k, this.x + this.k * e, this.y + this.k * t);
	},
	apply: function(e) {
		return [e[0] * this.k + this.x, e[1] * this.k + this.y];
	},
	applyX: function(e) {
		return e * this.k + this.x;
	},
	applyY: function(e) {
		return e * this.k + this.y;
	},
	invert: function(e) {
		return [(e[0] - this.x) / this.k, (e[1] - this.y) / this.k];
	},
	invertX: function(e) {
		return (e - this.x) / this.k;
	},
	invertY: function(e) {
		return (e - this.y) / this.k;
	},
	rescaleX: function(e) {
		return e.copy().domain(e.range().map(this.invertX, this).map(e.invert, e));
	},
	rescaleY: function(e) {
		return e.copy().domain(e.range().map(this.invertY, this).map(e.invert, e));
	},
	toString: function() {
		return "translate(" + this.x + "," + this.y + ") scale(" + this.k + ")";
	}
};
var ia = new ra(1, 0, 0);
aa.prototype = ra.prototype;
function aa(e) {
	for (; !e.__zoom;) if (!(e = e.parentNode)) return ia;
	return e.__zoom;
}
//#endregion
//#region node_modules/d3-zoom/src/noevent.js
function oa(e) {
	e.stopImmediatePropagation();
}
function sa(e) {
	e.preventDefault(), e.stopImmediatePropagation();
}
//#endregion
//#region node_modules/d3-zoom/src/zoom.js
function ca(e) {
	return (!e.ctrlKey || e.type === "wheel") && !e.button;
}
function la() {
	var e = this;
	return e instanceof SVGElement ? (e = e.ownerSVGElement || e, e.hasAttribute("viewBox") ? (e = e.viewBox.baseVal, [[e.x, e.y], [e.x + e.width, e.y + e.height]]) : [[0, 0], [e.width.baseVal.value, e.height.baseVal.value]]) : [[0, 0], [e.clientWidth, e.clientHeight]];
}
function ua() {
	return this.__zoom || ia;
}
function da(e) {
	return -e.deltaY * (e.deltaMode === 1 ? .05 : e.deltaMode ? 1 : .002) * (e.ctrlKey ? 10 : 1);
}
function fa() {
	return navigator.maxTouchPoints || "ontouchstart" in this;
}
function pa(e, t, n) {
	var r = e.invertX(t[0][0]) - n[0][0], i = e.invertX(t[1][0]) - n[1][0], a = e.invertY(t[0][1]) - n[0][1], o = e.invertY(t[1][1]) - n[1][1];
	return e.translate(i > r ? (r + i) / 2 : Math.min(0, r) || Math.max(0, i), o > a ? (a + o) / 2 : Math.min(0, a) || Math.max(0, o));
}
function ma() {
	var e = ca, t = la, n = pa, r = da, i = fa, a = [0, Infinity], o = [[-Infinity, -Infinity], [Infinity, Infinity]], s = 250, c = _r, l = w("start", "zoom", "end"), u, d, f, p = 500, m = 150, h = 0, g = 10;
	function _(e) {
		e.property("__zoom", ua).on("wheel.zoom", T, { passive: !1 }).on("mousedown.zoom", E).on("dblclick.zoom", D).filter(i).on("touchstart.zoom", O).on("touchmove.zoom", k).on("touchend.zoom touchcancel.zoom", A).style("-webkit-tap-highlight-color", "rgba(0,0,0,0)");
	}
	_.transform = function(e, t, n, r) {
		var i = e.selection ? e.selection() : e;
		i.property("__zoom", ua), e === i ? i.interrupt().each(function() {
			S(this, arguments).event(r).start().zoom(null, typeof t == "function" ? t.apply(this, arguments) : t).end();
		}) : x(e, t, n, r);
	}, _.scaleBy = function(e, t, n, r) {
		_.scaleTo(e, function() {
			return this.__zoom.k * (typeof t == "function" ? t.apply(this, arguments) : t);
		}, n, r);
	}, _.scaleTo = function(e, r, i, a) {
		_.transform(e, function() {
			var e = t.apply(this, arguments), a = this.__zoom, s = i == null ? b(e) : typeof i == "function" ? i.apply(this, arguments) : i, c = a.invert(s), l = typeof r == "function" ? r.apply(this, arguments) : r;
			return n(y(v(a, l), s, c), e, o);
		}, i, a);
	}, _.translateBy = function(e, r, i, a) {
		_.transform(e, function() {
			return n(this.__zoom.translate(typeof r == "function" ? r.apply(this, arguments) : r, typeof i == "function" ? i.apply(this, arguments) : i), t.apply(this, arguments), o);
		}, null, a);
	}, _.translateTo = function(e, r, i, a, s) {
		_.transform(e, function() {
			var e = t.apply(this, arguments), s = this.__zoom, c = a == null ? b(e) : typeof a == "function" ? a.apply(this, arguments) : a;
			return n(ia.translate(c[0], c[1]).scale(s.k).translate(typeof r == "function" ? -r.apply(this, arguments) : -r, typeof i == "function" ? -i.apply(this, arguments) : -i), e, o);
		}, a, s);
	};
	function v(e, t) {
		return t = Math.max(a[0], Math.min(a[1], t)), t === e.k ? e : new ra(t, e.x, e.y);
	}
	function y(e, t, n) {
		var r = t[0] - n[0] * e.k, i = t[1] - n[1] * e.k;
		return r === e.x && i === e.y ? e : new ra(e.k, r, i);
	}
	function b(e) {
		return [(+e[0][0] + +e[1][0]) / 2, (+e[0][1] + +e[1][1]) / 2];
	}
	function x(e, n, r, i) {
		e.on("start.zoom", function() {
			S(this, arguments).event(i).start();
		}).on("interrupt.zoom end.zoom", function() {
			S(this, arguments).event(i).end();
		}).tween("zoom", function() {
			var e = this, a = arguments, o = S(e, a).event(i), s = t.apply(e, a), l = r == null ? b(s) : typeof r == "function" ? r.apply(e, a) : r, u = Math.max(s[1][0] - s[0][0], s[1][1] - s[0][1]), d = e.__zoom, f = typeof n == "function" ? n.apply(e, a) : n, p = c(d.invert(l).concat(u / d.k), f.invert(l).concat(u / f.k));
			return function(e) {
				if (e === 1) e = f;
				else {
					var t = p(e), n = u / t[2];
					e = new ra(n, l[0] - t[0] * n, l[1] - t[1] * n);
				}
				o.zoom(null, e);
			};
		});
	}
	function S(e, t, n) {
		return !n && e.__zooming || new C(e, t);
	}
	function C(e, n) {
		this.that = e, this.args = n, this.active = 0, this.sourceEvent = null, this.extent = t.apply(e, n), this.taps = 0;
	}
	C.prototype = {
		event: function(e) {
			return e && (this.sourceEvent = e), this;
		},
		start: function() {
			return ++this.active === 1 && (this.that.__zooming = this, this.emit("start")), this;
		},
		zoom: function(e, t) {
			return this.mouse && e !== "mouse" && (this.mouse[1] = t.invert(this.mouse[0])), this.touch0 && e !== "touch" && (this.touch0[1] = t.invert(this.touch0[0])), this.touch1 && e !== "touch" && (this.touch1[1] = t.invert(this.touch1[0])), this.that.__zoom = t, this.emit("zoom"), this;
		},
		end: function() {
			return --this.active === 0 && (delete this.that.__zooming, this.emit("end")), this;
		},
		emit: function(e) {
			var t = Bt(this.that).datum();
			l.call(e, this.that, new na(e, {
				sourceEvent: this.sourceEvent,
				target: _,
				type: e,
				transform: this.that.__zoom,
				dispatch: l
			}), t);
		}
	};
	function T(t, ...i) {
		if (!e.apply(this, arguments)) return;
		var s = S(this, i).event(t), c = this.__zoom, l = Math.max(a[0], Math.min(a[1], c.k * 2 ** r.apply(this, arguments))), u = Vt(t);
		if (s.wheel) (s.mouse[0][0] !== u[0] || s.mouse[0][1] !== u[1]) && (s.mouse[1] = c.invert(s.mouse[0] = u)), clearTimeout(s.wheel);
		else if (c.k === l) return;
		else s.mouse = [u, c.invert(u)], Kr(this), s.start();
		sa(t), s.wheel = setTimeout(d, m), s.zoom("mouse", n(y(v(c, l), s.mouse[0], s.mouse[1]), s.extent, o));
		function d() {
			s.wheel = null, s.end();
		}
	}
	function E(t, ...r) {
		if (f || !e.apply(this, arguments)) return;
		var i = t.currentTarget, a = S(this, r, !0).event(t), s = Bt(t.view).on("mousemove.zoom", d, !0).on("mouseup.zoom", p, !0), c = Vt(t, i), l = t.clientX, u = t.clientY;
		Kt(t.view), oa(t), a.mouse = [c, this.__zoom.invert(c)], Kr(this), a.start();
		function d(e) {
			if (sa(e), !a.moved) {
				var t = e.clientX - l, r = e.clientY - u;
				a.moved = t * t + r * r > h;
			}
			a.event(e).zoom("mouse", n(y(a.that.__zoom, a.mouse[0] = Vt(e, i), a.mouse[1]), a.extent, o));
		}
		function p(e) {
			s.on("mousemove.zoom mouseup.zoom", null), qt(e.view, a.moved), sa(e), a.event(e).end();
		}
	}
	function D(r, ...i) {
		if (e.apply(this, arguments)) {
			var a = this.__zoom, c = Vt(r.changedTouches ? r.changedTouches[0] : r, this), l = a.invert(c), u = a.k * (r.shiftKey ? .5 : 2), d = n(y(v(a, u), c, l), t.apply(this, i), o);
			sa(r), s > 0 ? Bt(this).transition().duration(s).call(x, d, c, r) : Bt(this).call(_.transform, d, c, r);
		}
	}
	function O(t, ...n) {
		if (e.apply(this, arguments)) {
			var r = t.touches, i = r.length, a = S(this, n, t.changedTouches.length === i).event(t), o, s, c, l;
			for (oa(t), s = 0; s < i; ++s) c = r[s], l = Vt(c, this), l = [
				l,
				this.__zoom.invert(l),
				c.identifier
			], a.touch0 ? !a.touch1 && a.touch0[2] !== l[2] && (a.touch1 = l, a.taps = 0) : (a.touch0 = l, o = !0, a.taps = 1 + !!u);
			u &&= clearTimeout(u), o && (a.taps < 2 && (d = l[0], u = setTimeout(function() {
				u = null;
			}, p)), Kr(this), a.start());
		}
	}
	function k(e, ...t) {
		if (this.__zooming) {
			var r = S(this, t).event(e), i = e.changedTouches, a = i.length, s, c, l, u;
			for (sa(e), s = 0; s < a; ++s) c = i[s], l = Vt(c, this), r.touch0 && r.touch0[2] === c.identifier ? r.touch0[0] = l : r.touch1 && r.touch1[2] === c.identifier && (r.touch1[0] = l);
			if (c = r.that.__zoom, r.touch1) {
				var d = r.touch0[0], f = r.touch0[1], p = r.touch1[0], m = r.touch1[1], h = (h = p[0] - d[0]) * h + (h = p[1] - d[1]) * h, g = (g = m[0] - f[0]) * g + (g = m[1] - f[1]) * g;
				c = v(c, Math.sqrt(h / g)), l = [(d[0] + p[0]) / 2, (d[1] + p[1]) / 2], u = [(f[0] + m[0]) / 2, (f[1] + m[1]) / 2];
			} else if (r.touch0) l = r.touch0[0], u = r.touch0[1];
			else return;
			r.zoom("touch", n(y(c, l, u), r.extent, o));
		}
	}
	function A(e, ...t) {
		if (this.__zooming) {
			var n = S(this, t).event(e), r = e.changedTouches, i = r.length, a, o;
			for (oa(e), f && clearTimeout(f), f = setTimeout(function() {
				f = null;
			}, p), a = 0; a < i; ++a) o = r[a], n.touch0 && n.touch0[2] === o.identifier ? delete n.touch0 : n.touch1 && n.touch1[2] === o.identifier && delete n.touch1;
			if (n.touch1 && !n.touch0 && (n.touch0 = n.touch1, delete n.touch1), n.touch0) n.touch0[1] = this.__zoom.invert(n.touch0[0]);
			else if (n.end(), n.taps === 2 && (o = Vt(o, this), Math.hypot(d[0] - o[0], d[1] - o[1]) < g)) {
				var s = Bt(this).on("dblclick.zoom");
				s && s.apply(this, arguments);
			}
		}
	}
	return _.wheelDelta = function(e) {
		return arguments.length ? (r = typeof e == "function" ? e : ta(+e), _) : r;
	}, _.filter = function(t) {
		return arguments.length ? (e = typeof t == "function" ? t : ta(!!t), _) : e;
	}, _.touchable = function(e) {
		return arguments.length ? (i = typeof e == "function" ? e : ta(!!e), _) : i;
	}, _.extent = function(e) {
		return arguments.length ? (t = typeof e == "function" ? e : ta([[+e[0][0], +e[0][1]], [+e[1][0], +e[1][1]]]), _) : t;
	}, _.scaleExtent = function(e) {
		return arguments.length ? (a[0] = +e[0], a[1] = +e[1], _) : [a[0], a[1]];
	}, _.translateExtent = function(e) {
		return arguments.length ? (o[0][0] = +e[0][0], o[1][0] = +e[1][0], o[0][1] = +e[0][1], o[1][1] = +e[1][1], _) : [[o[0][0], o[0][1]], [o[1][0], o[1][1]]];
	}, _.constrain = function(e) {
		return arguments.length ? (n = e, _) : n;
	}, _.duration = function(e) {
		return arguments.length ? (s = +e, _) : s;
	}, _.interpolate = function(e) {
		return arguments.length ? (c = e, _) : c;
	}, _.on = function() {
		var e = l.on.apply(l, arguments);
		return e === l ? _ : e;
	}, _.clickDistance = function(e) {
		return arguments.length ? (h = (e = +e) * e, _) : Math.sqrt(h);
	}, _.tapDistance = function(e) {
		return arguments.length ? (g = +e, _) : g;
	}, _;
}
//#endregion
//#region node_modules/@xyflow/system/dist/esm/index.js
var ha = {
	error001: (e = "react") => `Seems like you have not used ${e === "svelte" ? "SvelteFlowProvider" : "ReactFlowProvider"} as an ancestor. Help: https://${e}flow.dev/error#001`,
	error002: () => "It looks like you've created a new nodeTypes or edgeTypes object. If this wasn't on purpose please define the nodeTypes/edgeTypes outside of the component or memoize them.",
	error003: (e) => `Node type "${e}" not found. Using fallback type "default".`,
	error004: () => "The parent container needs a width and a height to render the graph.",
	error005: () => "Only child nodes can use a parent extent.",
	error006: () => "Can't create edge. An edge needs a source and a target.",
	error007: (e) => `The old edge with id=${e} does not exist.`,
	error009: (e) => `Marker type "${e}" doesn't exist.`,
	error008: (e, { id: t, sourceHandle: n, targetHandle: r }) => `Couldn't create edge for ${e} handle id: "${e === "source" ? n : r}", edge id: ${t}.`,
	error010: () => "Handle: No node id found. Make sure to only use a Handle inside a custom Node.",
	error011: (e) => `Edge type "${e}" not found. Using fallback type "default".`,
	error012: (e) => `Node with id "${e}" does not exist, it may have been removed. This can happen when a node is deleted before the "onNodeClick" handler is called.`,
	error013: (e = "react") => `It seems that you haven't loaded the styles. Please import '@xyflow/${e}/dist/style.css' or base.css to make sure everything is working properly.`,
	error014: () => "useNodeConnections: No node ID found. Call useNodeConnections inside a custom Node or provide a node ID.",
	error015: () => "It seems that you are trying to drag a node that is not initialized. Please use onNodesChange as explained in the docs.",
	error016: (e) => `Edge with id "${e}" does not exist, it may have been removed. This can happen when an edge is deleted before the "onEdgeClick" handler is called.`
}, ga = [[-Infinity, -Infinity], [Infinity, Infinity]], _a = [
	"Enter",
	" ",
	"Escape"
], va = {
	"node.a11yDescription.default": "Press enter or space to select a node. Press delete to remove it and escape to cancel.",
	"node.a11yDescription.keyboardDisabled": "Press enter or space to select a node. You can then use the arrow keys to move the node around. Press delete to remove it and escape to cancel.",
	"node.a11yDescription.ariaLiveMessage": ({ direction: e, x: t, y: n }) => `Moved selected node ${e}. New position, x: ${t}, y: ${n}`,
	"edge.a11yDescription.default": "Press enter or space to select an edge. You can then press delete to remove it or escape to cancel.",
	"controls.ariaLabel": "Control Panel",
	"controls.zoomIn.ariaLabel": "Zoom In",
	"controls.zoomOut.ariaLabel": "Zoom Out",
	"controls.fitView.ariaLabel": "Fit View",
	"controls.interactive.ariaLabel": "Toggle Interactivity",
	"minimap.ariaLabel": "Mini Map",
	"handle.ariaLabel": "Handle"
}, ya;
(function(e) {
	e.Strict = "strict", e.Loose = "loose";
})(ya ||= {});
var ba;
(function(e) {
	e.Free = "free", e.Vertical = "vertical", e.Horizontal = "horizontal";
})(ba ||= {});
var xa;
(function(e) {
	e.Partial = "partial", e.Full = "full";
})(xa ||= {});
var Sa = {
	inProgress: !1,
	isValid: null,
	from: null,
	fromHandle: null,
	fromPosition: null,
	fromNode: null,
	to: null,
	toHandle: null,
	toPosition: null,
	toNode: null,
	pointer: null
}, K;
(function(e) {
	e.Bezier = "default", e.Straight = "straight", e.Step = "step", e.SmoothStep = "smoothstep", e.SimpleBezier = "simplebezier";
})(K ||= {});
var Ca;
(function(e) {
	e.Arrow = "arrow", e.ArrowClosed = "arrowclosed";
})(Ca ||= {});
var q;
(function(e) {
	e.Left = "left", e.Top = "top", e.Right = "right", e.Bottom = "bottom";
})(q ||= {});
var wa = {
	[q.Left]: q.Right,
	[q.Right]: q.Left,
	[q.Top]: q.Bottom,
	[q.Bottom]: q.Top
};
function Ta(e) {
	return e === null ? null : e ? "valid" : "invalid";
}
var Ea = (e) => "id" in e && "source" in e && "target" in e, Da = (e) => "id" in e && "position" in e && !("source" in e) && !("target" in e), Oa = (e) => "id" in e && "internals" in e && !("source" in e) && !("target" in e), ka = (e, t = [0, 0]) => {
	let { width: n, height: r } = lo(e), i = e.origin ?? t, a = n * i[0], o = r * i[1];
	return {
		x: e.position.x - a,
		y: e.position.y - o
	};
}, Aa = (e, t = { nodeOrigin: [0, 0] }) => e.length === 0 ? {
	x: 0,
	y: 0,
	width: 0,
	height: 0
} : Ga(e.reduce((e, n) => {
	let r = typeof n == "string", i = !t.nodeLookup && !r ? n : void 0;
	return t.nodeLookup && (i = r ? t.nodeLookup.get(n) : Oa(n) ? n : t.nodeLookup.get(n.id)), Ua(e, i ? qa(i, t.nodeOrigin) : {
		x: 0,
		y: 0,
		x2: 0,
		y2: 0
	});
}, {
	x: Infinity,
	y: Infinity,
	x2: -Infinity,
	y2: -Infinity
})), ja = (e, t = {}) => {
	let n = {
		x: Infinity,
		y: Infinity,
		x2: -Infinity,
		y2: -Infinity
	}, r = !1;
	return e.forEach((e) => {
		(t.filter === void 0 || t.filter(e)) && (n = Ua(n, qa(e)), r = !0);
	}), r ? Ga(n) : {
		x: 0,
		y: 0,
		width: 0,
		height: 0
	};
}, Ma = (e, t, [n, r, i] = [
	0,
	0,
	1
], a = !1, o = !1) => {
	let s = (t.x - n) / i, c = (t.y - r) / i, l = t.width / i, u = t.height / i, d = [];
	for (let t of e.values()) {
		let { measured: e, selectable: n = !0, hidden: r = !1 } = t;
		if (o && !n || r) continue;
		let i = e.width ?? t.width ?? t.initialWidth ?? 0, f = e.height ?? t.height ?? t.initialHeight ?? 0, { x: p, y: m } = t.internals.positionAbsolute, h = Ya(s, c, l, u, p, m, i, f), g = i * f, _ = a && h > 0;
		(!t.internals.handleBounds || _ || h >= g || t.dragging) && d.push(t);
	}
	return d;
}, Na = (e, t) => {
	let n = /* @__PURE__ */ new Set();
	return e.forEach((e) => {
		n.add(e.id);
	}), t.filter((e) => n.has(e.source) || n.has(e.target));
};
function Pa(e, t) {
	let n = /* @__PURE__ */ new Map(), r = t?.nodes ? new Set(t.nodes.map((e) => e.id)) : null;
	return e.forEach((e) => {
		e.measured.width && e.measured.height && (t?.includeHiddenNodes || !e.hidden) && (!r || r.has(e.id)) && n.set(e.id, e);
	}), n;
}
async function Fa({ nodes: e, width: t, height: n, panZoom: r, minZoom: i, maxZoom: a }, o) {
	if (e.size === 0) return !0;
	let s = oo(ja(Pa(e, o)), t, n, o?.minZoom ?? i, o?.maxZoom ?? a, o?.padding ?? .1);
	return await r.setViewport(s, {
		duration: o?.duration,
		ease: o?.ease,
		interpolate: o?.interpolate
	}), !0;
}
function Ia({ nodeId: e, nextPosition: t, nodeLookup: n, nodeOrigin: r = [0, 0], nodeExtent: i, onError: a }) {
	let o = n.get(e), s = o.parentId ? n.get(o.parentId) : void 0, { x: c, y: l } = s ? s.internals.positionAbsolute : {
		x: 0,
		y: 0
	}, u = o.origin ?? r, d = o.extent || i;
	if (o.extent === "parent" && !o.expandParent) if (!s) a?.("005", ha.error005());
	else {
		let e = s.measured.width, t = s.measured.height;
		e && t && (d = [[c, l], [c + e, l + t]]);
	}
	else s && co(o.extent) && (d = [[o.extent[0][0] + c, o.extent[0][1] + l], [o.extent[1][0] + c, o.extent[1][1] + l]]);
	let f = co(d) ? za(t, d, o.measured) : t;
	return (o.measured.width === void 0 || o.measured.height === void 0) && a?.("015", ha.error015()), {
		position: {
			x: f.x - c + (o.measured.width ?? 0) * u[0],
			y: f.y - l + (o.measured.height ?? 0) * u[1]
		},
		positionAbsolute: f
	};
}
async function La({ nodesToRemove: e = [], edgesToRemove: t = [], nodes: n, edges: r, onBeforeDelete: i }) {
	let a = new Set(e.map((e) => e.id)), o = [];
	for (let e of n) {
		if (e.deletable === !1) continue;
		let t = a.has(e.id), n = !t && e.parentId && o.find((t) => t.id === e.parentId);
		(t || n) && o.push(e);
	}
	let s = new Set(t.map((e) => e.id)), c = r.filter((e) => e.deletable !== !1), l = Na(o, c);
	for (let e of c) s.has(e.id) && !l.find((t) => t.id === e.id) && l.push(e);
	if (!i) return {
		edges: l,
		nodes: o
	};
	let u = await i({
		nodes: o,
		edges: l
	});
	return typeof u == "boolean" ? u ? {
		edges: l,
		nodes: o
	} : {
		edges: [],
		nodes: []
	} : u;
}
var Ra = (e, t = 0, n = 1) => Math.min(Math.max(e, t), n), za = (e = {
	x: 0,
	y: 0
}, t, n) => ({
	x: Ra(e.x, t[0][0], t[1][0] - (n?.width ?? 0)),
	y: Ra(e.y, t[0][1], t[1][1] - (n?.height ?? 0))
});
function Ba(e, t, n) {
	let { width: r, height: i } = lo(n), { x: a, y: o } = n.internals.positionAbsolute;
	return za(e, [[a, o], [a + r, o + i]], t);
}
var Va = (e, t, n) => e < t ? Ra(Math.abs(e - t), 1, t) / t : e > n ? -Ra(Math.abs(e - n), 1, t) / t : 0, Ha = (e, t, n = 15, r = 40) => [Va(e.x, r, t.width - r) * n, Va(e.y, r, t.height - r) * n], Ua = (e, t) => ({
	x: Math.min(e.x, t.x),
	y: Math.min(e.y, t.y),
	x2: Math.max(e.x2, t.x2),
	y2: Math.max(e.y2, t.y2)
}), Wa = ({ x: e, y: t, width: n, height: r }) => ({
	x: e,
	y: t,
	x2: e + n,
	y2: t + r
}), Ga = ({ x: e, y: t, x2: n, y2: r }) => ({
	x: e,
	y: t,
	width: n - e,
	height: r - t
}), Ka = (e, t = [0, 0]) => {
	let { x: n, y: r } = Oa(e) ? e.internals.positionAbsolute : ka(e, t);
	return {
		x: n,
		y: r,
		width: e.measured?.width ?? e.width ?? e.initialWidth ?? 0,
		height: e.measured?.height ?? e.height ?? e.initialHeight ?? 0
	};
}, qa = (e, t = [0, 0]) => {
	let { x: n, y: r } = Oa(e) ? e.internals.positionAbsolute : ka(e, t);
	return {
		x: n,
		y: r,
		x2: n + (e.measured?.width ?? e.width ?? e.initialWidth ?? 0),
		y2: r + (e.measured?.height ?? e.height ?? e.initialHeight ?? 0)
	};
}, Ja = (e, t) => Ga(Ua(Wa(e), Wa(t))), Ya = (e, t, n, r, i, a, o, s) => {
	let c = Math.max(0, Math.min(e + n, i + o) - Math.max(e, i)), l = Math.max(0, Math.min(t + r, a + s) - Math.max(t, a));
	return Math.ceil(c * l);
}, Xa = (e, t) => Ya(e.x, e.y, e.width, e.height, t.x, t.y, t.width, t.height), Za = (e) => Qa(e.width) && Qa(e.height) && Qa(e.x) && Qa(e.y), Qa = (e) => !isNaN(e) && isFinite(e), $a = (e, t) => (e, t) => {}, eo = (e, t = [1, 1]) => ({
	x: t[0] * Math.round(e.x / t[0]),
	y: t[1] * Math.round(e.y / t[1])
}), to = ({ x: e, y: t }, [n, r, i], a = !1, o = [1, 1]) => {
	let s = {
		x: (e - n) / i,
		y: (t - r) / i
	};
	return a ? eo(s, o) : s;
}, no = ({ x: e, y: t }, [n, r, i]) => ({
	x: e * i + n,
	y: t * i + r
});
function ro(e, t) {
	if (typeof e == "number") return Math.floor((t - t / (1 + e)) * .5);
	if (typeof e == "string" && e.endsWith("px")) {
		let t = parseFloat(e);
		if (!Number.isNaN(t)) return Math.floor(t);
	}
	if (typeof e == "string" && e.endsWith("%")) {
		let n = parseFloat(e);
		if (!Number.isNaN(n)) return Math.floor(t * n * .01);
	}
	return console.error(`The padding value "${e}" is invalid. Please provide a number or a string with a valid unit (px or %).`), 0;
}
function io(e, t, n) {
	if (typeof e == "string" || typeof e == "number") {
		let r = ro(e, n), i = ro(e, t);
		return {
			top: r,
			right: i,
			bottom: r,
			left: i,
			x: i * 2,
			y: r * 2
		};
	}
	if (typeof e == "object") {
		let r = ro(e.top ?? e.y ?? 0, n), i = ro(e.bottom ?? e.y ?? 0, n), a = ro(e.left ?? e.x ?? 0, t), o = ro(e.right ?? e.x ?? 0, t);
		return {
			top: r,
			right: o,
			bottom: i,
			left: a,
			x: a + o,
			y: r + i
		};
	}
	return {
		top: 0,
		right: 0,
		bottom: 0,
		left: 0,
		x: 0,
		y: 0
	};
}
function ao(e, t, n, r, i, a) {
	let { x: o, y: s } = no(e, [
		t,
		n,
		r
	]), { x: c, y: l } = no({
		x: e.x + e.width,
		y: e.y + e.height
	}, [
		t,
		n,
		r
	]), u = i - c, d = a - l;
	return {
		left: Math.floor(o),
		top: Math.floor(s),
		right: Math.floor(u),
		bottom: Math.floor(d)
	};
}
var oo = (e, t, n, r, i, a) => {
	let o = io(a, t, n), s = (t - o.x) / e.width, c = (n - o.y) / e.height, l = Ra(Math.min(s, c), r, i), u = e.x + e.width / 2, d = e.y + e.height / 2, f = t / 2 - u * l, p = n / 2 - d * l, m = ao(e, f, p, l, t, n), h = {
		left: Math.min(m.left - o.left, 0),
		top: Math.min(m.top - o.top, 0),
		right: Math.min(m.right - o.right, 0),
		bottom: Math.min(m.bottom - o.bottom, 0)
	};
	return {
		x: f - h.left + h.right,
		y: p - h.top + h.bottom,
		zoom: l
	};
}, so = () => typeof navigator < "u" && navigator?.userAgent?.indexOf("Mac") >= 0;
function co(e) {
	return e != null && e !== "parent";
}
function lo(e) {
	return {
		width: e.measured?.width ?? e.width ?? e.initialWidth ?? 0,
		height: e.measured?.height ?? e.height ?? e.initialHeight ?? 0
	};
}
function uo(e) {
	return (e.measured?.width ?? e.width ?? e.initialWidth) !== void 0 && (e.measured?.height ?? e.height ?? e.initialHeight) !== void 0;
}
function fo(e, t = {
	width: 0,
	height: 0
}, n, r, i) {
	let a = { ...e }, o = r.get(n);
	if (o) {
		let e = o.origin || i;
		a.x += o.internals.positionAbsolute.x - (t.width ?? 0) * e[0], a.y += o.internals.positionAbsolute.y - (t.height ?? 0) * e[1];
	}
	return a;
}
function po(e, t) {
	if (e.size !== t.size) return !1;
	for (let n of e) if (!t.has(n)) return !1;
	return !0;
}
function mo() {
	let e, t;
	return {
		promise: new Promise((n, r) => {
			e = n, t = r;
		}),
		resolve: e,
		reject: t
	};
}
function ho(e) {
	return {
		...va,
		...e || {}
	};
}
function go(e, { snapGrid: t = [0, 0], snapToGrid: n = !1, transform: r, containerBounds: i }) {
	let { x: a, y: o } = xo(e), s = to({
		x: a - (i?.left ?? 0),
		y: o - (i?.top ?? 0)
	}, r), { x: c, y: l } = n ? eo(s, t) : s;
	return {
		xSnapped: c,
		ySnapped: l,
		...s
	};
}
var J = (e) => ({
	width: e.offsetWidth,
	height: e.offsetHeight
}), _o = (e) => e?.getRootNode?.() || window?.document, vo = [
	"INPUT",
	"SELECT",
	"TEXTAREA"
];
function yo(e) {
	let t = e.composedPath?.()?.[0] || e.target;
	return t?.nodeType === 1 ? vo.includes(t.nodeName) || t.hasAttribute("contenteditable") || !!t.closest(".nokey") : !1;
}
var bo = (e) => "clientX" in e, xo = (e, t) => {
	let n = bo(e), r = n ? e.clientX : e.touches?.[0].clientX, i = n ? e.clientY : e.touches?.[0].clientY;
	return {
		x: r - (t?.left ?? 0),
		y: i - (t?.top ?? 0)
	};
}, So = (e, t, n, r, i) => {
	let a = t.querySelectorAll(`.${e}`);
	return !a || !a.length ? null : Array.from(a).map((t) => {
		let a = t.getBoundingClientRect();
		return {
			id: t.getAttribute("data-handleid"),
			type: e,
			nodeId: i,
			position: t.getAttribute("data-handlepos"),
			x: (a.left - n.left) / r,
			y: (a.top - n.top) / r,
			...J(t)
		};
	});
};
function Co({ sourceX: e, sourceY: t, targetX: n, targetY: r, sourceControlX: i, sourceControlY: a, targetControlX: o, targetControlY: s }) {
	let c = e * .125 + i * .375 + o * .375 + n * .125, l = t * .125 + a * .375 + s * .375 + r * .125;
	return [
		c,
		l,
		Math.abs(c - e),
		Math.abs(l - t)
	];
}
function wo(e, t) {
	return e >= 0 ? .5 * e : t * 25 * Math.sqrt(-e);
}
function To({ pos: e, x1: t, y1: n, x2: r, y2: i, c: a }) {
	switch (e) {
		case q.Left: return [t - wo(t - r, a), n];
		case q.Right: return [t + wo(r - t, a), n];
		case q.Top: return [t, n - wo(n - i, a)];
		case q.Bottom: return [t, n + wo(i - n, a)];
	}
}
function Eo({ sourceX: e, sourceY: t, sourcePosition: n = q.Bottom, targetX: r, targetY: i, targetPosition: a = q.Top, curvature: o = .25 }) {
	let [s, c] = To({
		pos: n,
		x1: e,
		y1: t,
		x2: r,
		y2: i,
		c: o
	}), [l, u] = To({
		pos: a,
		x1: r,
		y1: i,
		x2: e,
		y2: t,
		c: o
	}), [d, f, p, m] = Co({
		sourceX: e,
		sourceY: t,
		targetX: r,
		targetY: i,
		sourceControlX: s,
		sourceControlY: c,
		targetControlX: l,
		targetControlY: u
	});
	return [
		`M${e},${t} C${s},${c} ${l},${u} ${r},${i}`,
		d,
		f,
		p,
		m
	];
}
function Do({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
	let i = Math.abs(n - e) / 2, a = n < e ? n + i : n - i, o = Math.abs(r - t) / 2;
	return [
		a,
		r < t ? r + o : r - o,
		i,
		o
	];
}
function Oo({ sourceNode: e, targetNode: t, selected: n = !1, zIndex: r = 0, elevateOnSelect: i = !1, zIndexMode: a = "basic" }) {
	return a === "manual" ? r : (i && n ? r + 1e3 : r) + Math.max(e.parentId || i && e.selected ? e.internals.z : 0, t.parentId || i && t.selected ? t.internals.z : 0);
}
function ko({ sourceNode: e, targetNode: t, width: n, height: r, transform: i }) {
	let a = Ua(qa(e), qa(t));
	return a.x === a.x2 && (a.x2 += 1), a.y === a.y2 && (a.y2 += 1), Xa({
		x: -i[0] / i[2],
		y: -i[1] / i[2],
		width: n / i[2],
		height: r / i[2]
	}, Ga(a)) > 0;
}
var Ao = ({ source: e, sourceHandle: t, target: n, targetHandle: r }) => `xy-edge__${e}${t || ""}-${n}${r || ""}`, jo = (e, t) => t.some((t) => t.source === e.source && t.target === e.target && (t.sourceHandle === e.sourceHandle || !t.sourceHandle && !e.sourceHandle) && (t.targetHandle === e.targetHandle || !t.targetHandle && !e.targetHandle)), Mo = (e, t, n = {}) => {
	if (!e.source || !e.target) return n.onError?.("006", ha.error006()), t;
	let r = n.getEdgeId || Ao, i;
	return i = Ea(e) ? { ...e } : {
		...e,
		id: r(e)
	}, jo(i, t) ? t : (i.sourceHandle === null && delete i.sourceHandle, i.targetHandle === null && delete i.targetHandle, t.concat(i));
};
function No({ sourceX: e, sourceY: t, targetX: n, targetY: r }) {
	let [i, a, o, s] = Do({
		sourceX: e,
		sourceY: t,
		targetX: n,
		targetY: r
	});
	return [
		`M ${e},${t}L ${n},${r}`,
		i,
		a,
		o,
		s
	];
}
var Po = {
	[q.Left]: {
		x: -1,
		y: 0
	},
	[q.Right]: {
		x: 1,
		y: 0
	},
	[q.Top]: {
		x: 0,
		y: -1
	},
	[q.Bottom]: {
		x: 0,
		y: 1
	}
}, Fo = ({ source: e, sourcePosition: t = q.Bottom, target: n }) => t === q.Left || t === q.Right ? e.x < n.x ? {
	x: 1,
	y: 0
} : {
	x: -1,
	y: 0
} : e.y < n.y ? {
	x: 0,
	y: 1
} : {
	x: 0,
	y: -1
}, Io = (e, t) => Math.sqrt((t.x - e.x) ** 2 + (t.y - e.y) ** 2);
function Lo({ source: e, sourcePosition: t = q.Bottom, target: n, targetPosition: r = q.Top, center: i, offset: a, stepPosition: o }) {
	let s = Po[t], c = Po[r], l = {
		x: e.x + s.x * a,
		y: e.y + s.y * a
	}, u = {
		x: n.x + c.x * a,
		y: n.y + c.y * a
	}, d = Fo({
		source: l,
		sourcePosition: t,
		target: u
	}), f = d.x === 0 ? "y" : "x", p = d[f], m = [], h, g, _ = {
		x: 0,
		y: 0
	}, v = {
		x: 0,
		y: 0
	}, [, , y, b] = Do({
		sourceX: e.x,
		sourceY: e.y,
		targetX: n.x,
		targetY: n.y
	});
	if (s[f] * c[f] === -1) {
		f === "x" ? (h = i.x ?? l.x + (u.x - l.x) * o, g = i.y ?? (l.y + u.y) / 2) : (h = i.x ?? (l.x + u.x) / 2, g = i.y ?? l.y + (u.y - l.y) * o);
		let e = [{
			x: h,
			y: l.y
		}, {
			x: h,
			y: u.y
		}], t = [{
			x: l.x,
			y: g
		}, {
			x: u.x,
			y: g
		}];
		m = s[f] === p ? f === "x" ? e : t : f === "x" ? t : e;
	} else {
		let i = [{
			x: l.x,
			y: u.y
		}], o = [{
			x: u.x,
			y: l.y
		}];
		if (m = f === "x" ? s.x === p ? o : i : s.y === p ? i : o, t === r) {
			let t = Math.abs(e[f] - n[f]);
			if (t <= a) {
				let r = Math.min(a - 1, a - t);
				s[f] === p ? _[f] = (l[f] > e[f] ? -1 : 1) * r : v[f] = (u[f] > n[f] ? -1 : 1) * r;
			}
		}
		if (t !== r) {
			let e = f === "x" ? "y" : "x", t = s[f] === c[e], n = l[e] > u[e], r = l[e] < u[e];
			(s[f] === 1 && (!t && n || t && r) || s[f] !== 1 && (!t && r || t && n)) && (m = f === "x" ? i : o);
		}
		let d = {
			x: l.x + _.x,
			y: l.y + _.y
		}, y = {
			x: u.x + v.x,
			y: u.y + v.y
		};
		Math.max(Math.abs(d.x - m[0].x), Math.abs(y.x - m[0].x)) >= Math.max(Math.abs(d.y - m[0].y), Math.abs(y.y - m[0].y)) ? (h = (d.x + y.x) / 2, g = m[0].y) : (h = m[0].x, g = (d.y + y.y) / 2);
	}
	let x = {
		x: l.x + _.x,
		y: l.y + _.y
	}, S = {
		x: u.x + v.x,
		y: u.y + v.y
	};
	return [
		[
			e,
			...x.x !== m[0].x || x.y !== m[0].y ? [x] : [],
			...m,
			...S.x !== m[m.length - 1].x || S.y !== m[m.length - 1].y ? [S] : [],
			n
		],
		h,
		g,
		y,
		b
	];
}
function Ro(e, t, n, r) {
	let i = Math.min(Io(e, t) / 2, Io(t, n) / 2, r), { x: a, y: o } = t;
	if (e.x === a && a === n.x || e.y === o && o === n.y) return `L${a} ${o}`;
	if (e.y === o) {
		let t = e.x < n.x ? -1 : 1, r = e.y < n.y ? 1 : -1;
		return `L ${a + i * t},${o}Q ${a},${o} ${a},${o + i * r}`;
	}
	let s = e.x < n.x ? 1 : -1;
	return `L ${a},${o + i * (e.y < n.y ? -1 : 1)}Q ${a},${o} ${a + i * s},${o}`;
}
function zo({ sourceX: e, sourceY: t, sourcePosition: n = q.Bottom, targetX: r, targetY: i, targetPosition: a = q.Top, borderRadius: o = 5, centerX: s, centerY: c, offset: l = 20, stepPosition: u = .5 }) {
	let [d, f, p, m, h] = Lo({
		source: {
			x: e,
			y: t
		},
		sourcePosition: n,
		target: {
			x: r,
			y: i
		},
		targetPosition: a,
		center: {
			x: s,
			y: c
		},
		offset: l,
		stepPosition: u
	}), g = `M${d[0].x} ${d[0].y}`;
	for (let e = 1; e < d.length - 1; e++) g += Ro(d[e - 1], d[e], d[e + 1], o);
	return g += `L${d[d.length - 1].x} ${d[d.length - 1].y}`, [
		g,
		f,
		p,
		m,
		h
	];
}
function Bo(e) {
	return e && !!(e.internals.handleBounds || e.handles?.length) && !!(e.measured.width || e.width || e.initialWidth);
}
function Vo(e) {
	let { sourceNode: t, targetNode: n } = e;
	if (!Bo(t) || !Bo(n)) return null;
	let r = t.internals.handleBounds || Ho(t.handles), i = n.internals.handleBounds || Ho(n.handles), a = Wo(r?.source ?? [], e.sourceHandle), o = Wo(e.connectionMode === ya.Strict ? i?.target ?? [] : (i?.target ?? []).concat(i?.source ?? []), e.targetHandle);
	if (!a || !o) return e.onError?.("008", ha.error008(a ? "target" : "source", {
		id: e.id,
		sourceHandle: e.sourceHandle,
		targetHandle: e.targetHandle
	})), null;
	let s = a?.position || q.Bottom, c = o?.position || q.Top, l = Uo(t, a, s), u = Uo(n, o, c);
	return {
		sourceX: l.x,
		sourceY: l.y,
		targetX: u.x,
		targetY: u.y,
		sourcePosition: s,
		targetPosition: c
	};
}
function Ho(e) {
	if (!e) return null;
	let t = [], n = [];
	for (let r of e) r.width = r.width ?? 1, r.height = r.height ?? 1, r.type === "source" ? t.push(r) : r.type === "target" && n.push(r);
	return {
		source: t,
		target: n
	};
}
function Uo(e, t, n = q.Left, r = !1) {
	let i = (t?.x ?? 0) + e.internals.positionAbsolute.x, a = (t?.y ?? 0) + e.internals.positionAbsolute.y, { width: o, height: s } = t ?? lo(e);
	if (r) return {
		x: i + o / 2,
		y: a + s / 2
	};
	switch (t?.position ?? n) {
		case q.Top: return {
			x: i + o / 2,
			y: a
		};
		case q.Right: return {
			x: i + o,
			y: a + s / 2
		};
		case q.Bottom: return {
			x: i + o / 2,
			y: a + s
		};
		case q.Left: return {
			x: i,
			y: a + s / 2
		};
	}
}
function Wo(e, t) {
	return e && (t ? e.find((e) => e.id === t) : e[0]) || null;
}
function Go(e, t) {
	return e ? typeof e == "string" ? e : `${t ? `${t}__` : ""}${Object.keys(e).sort().map((t) => `${t}=${e[t]}`).join("&")}` : "";
}
function Ko(e, { id: t, defaultColor: n, defaultMarkerStart: r, defaultMarkerEnd: i }) {
	let a = /* @__PURE__ */ new Set();
	return e.reduce((e, o) => ([o.markerStart || r, o.markerEnd || i].forEach((r) => {
		if (r && typeof r == "object") {
			let i = Go(r, t);
			a.has(i) || (e.push({
				id: i,
				color: r.color || n,
				...r
			}), a.add(i));
		}
	}), e), []).sort((e, t) => e.id.localeCompare(t.id));
}
var qo = 1e3, Jo = 10, Yo = {
	nodeOrigin: [0, 0],
	nodeExtent: ga,
	elevateNodesOnSelect: !0,
	zIndexMode: "basic",
	defaults: {}
}, Xo = {
	...Yo,
	checkEquality: !0
};
function Zo(e, t) {
	let n = { ...e };
	for (let e in t) t[e] !== void 0 && (n[e] = t[e]);
	return n;
}
function Qo(e, t, n) {
	let r = Zo(Yo, n);
	for (let n of e.values()) if (n.parentId) rs(n, e, t, r);
	else {
		let e = za(ka(n, r.nodeOrigin), co(n.extent) ? n.extent : r.nodeExtent, lo(n));
		n.internals.positionAbsolute = e;
	}
}
function $o(e, t) {
	if (!e.handles) return e.measured ? t?.internals.handleBounds : void 0;
	let n = [], r = [];
	for (let t of e.handles) {
		let i = {
			id: t.id,
			width: t.width ?? 1,
			height: t.height ?? 1,
			nodeId: e.id,
			x: t.x,
			y: t.y,
			position: t.position,
			type: t.type
		};
		t.type === "source" ? n.push(i) : t.type === "target" && r.push(i);
	}
	return {
		source: n,
		target: r
	};
}
function es(e) {
	return e === "manual";
}
function ts(e, t, n, r = {}) {
	let i = Zo(Xo, r), a = { i: 0 }, o = new Map(t), s = i?.elevateNodesOnSelect && !es(i.zIndexMode) ? qo : 0, c = e.length > 0, l = !1;
	t.clear(), n.clear();
	for (let u of e) {
		let e = o.get(u.id);
		if (i.checkEquality && u === e?.internals.userNode) t.set(u.id, e);
		else {
			let n = za(ka(u, i.nodeOrigin), co(u.extent) ? u.extent : i.nodeExtent, lo(u));
			e = {
				...i.defaults,
				...u,
				measured: {
					width: u.measured?.width,
					height: u.measured?.height
				},
				internals: {
					positionAbsolute: n,
					handleBounds: $o(u, e),
					z: is(u, s, i.zIndexMode),
					userNode: u
				}
			}, t.set(u.id, e);
		}
		(e.measured === void 0 || e.measured.width === void 0 || e.measured.height === void 0) && !e.hidden && (c = !1), u.parentId && rs(e, t, n, r, a), l ||= u.selected ?? !1;
	}
	return {
		nodesInitialized: c,
		hasSelectedNodes: l
	};
}
function ns(e, t) {
	if (!e.parentId) return;
	let n = t.get(e.parentId);
	n ? n.set(e.id, e) : t.set(e.parentId, /* @__PURE__ */ new Map([[e.id, e]]));
}
function rs(e, t, n, r, i) {
	let { elevateNodesOnSelect: a, nodeOrigin: o, nodeExtent: s, zIndexMode: c } = Zo(Yo, r), l = e.parentId, u = t.get(l);
	if (!u) {
		console.warn(`Parent node ${l} not found. Please make sure that parent nodes are in front of their child nodes in the nodes array.`);
		return;
	}
	ns(e, n), i && !u.parentId && u.internals.rootParentIndex === void 0 && c === "auto" && (u.internals.rootParentIndex = ++i.i, u.internals.z = u.internals.z + i.i * Jo), i && u.internals.rootParentIndex !== void 0 && (i.i = u.internals.rootParentIndex);
	let { x: d, y: f, z: p } = as(e, u, o, s, a && !es(c) ? qo : 0, c), { positionAbsolute: m } = e.internals, h = d !== m.x || f !== m.y;
	(h || p !== e.internals.z) && t.set(e.id, {
		...e,
		internals: {
			...e.internals,
			positionAbsolute: h ? {
				x: d,
				y: f
			} : m,
			z: p
		}
	});
}
function is(e, t, n) {
	let r = Qa(e.zIndex) ? e.zIndex : 0;
	return es(n) ? r : r + (e.selected ? t : 0);
}
function as(e, t, n, r, i, a) {
	let { x: o, y: s } = t.internals.positionAbsolute, c = lo(e), l = ka(e, n), u = co(e.extent) ? za(l, e.extent, c) : l, d = za({
		x: o + u.x,
		y: s + u.y
	}, r, c);
	e.extent === "parent" && (d = Ba(d, c, t));
	let f = is(e, i, a), p = t.internals.z ?? 0;
	return {
		x: d.x,
		y: d.y,
		z: p >= f ? p + 1 : f
	};
}
function os(e, t, n, r = [0, 0]) {
	let i = [], a = /* @__PURE__ */ new Map();
	for (let n of e) {
		let e = t.get(n.parentId);
		if (!e) continue;
		let r = Ja(a.get(n.parentId)?.expandedRect ?? Ka(e), n.rect);
		a.set(n.parentId, {
			expandedRect: r,
			parent: e
		});
	}
	return a.size > 0 && a.forEach(({ expandedRect: t, parent: a }, o) => {
		let s = a.internals.positionAbsolute, c = lo(a), l = a.origin ?? r, u = t.x < s.x ? Math.round(Math.abs(s.x - t.x)) : 0, d = t.y < s.y ? Math.round(Math.abs(s.y - t.y)) : 0, f = Math.max(c.width, Math.round(t.width)), p = Math.max(c.height, Math.round(t.height)), m = (f - c.width) * l[0], h = (p - c.height) * l[1];
		(u > 0 || d > 0 || m || h) && (i.push({
			id: o,
			type: "position",
			position: {
				x: a.position.x - u + m,
				y: a.position.y - d + h
			}
		}), n.get(o)?.forEach((t) => {
			e.some((e) => e.id === t.id) || i.push({
				id: t.id,
				type: "position",
				position: {
					x: t.position.x + u,
					y: t.position.y + d
				}
			});
		})), (c.width < t.width || c.height < t.height || u || d) && i.push({
			id: o,
			type: "dimensions",
			setAttributes: !0,
			dimensions: {
				width: f + (u ? l[0] * u - m : 0),
				height: p + (d ? l[1] * d - h : 0)
			}
		});
	}), i;
}
function ss(e, t, n, r, i, a, o) {
	let s = r?.querySelector(".xyflow__viewport"), c = !1;
	if (!s) return {
		changes: [],
		updatedInternals: c
	};
	let l = [], u = window.getComputedStyle(s), { m22: d } = new window.DOMMatrixReadOnly(u.transform), f = [];
	for (let r of e.values()) {
		let e = t.get(r.id);
		if (!e) continue;
		if (e.hidden) {
			t.set(e.id, {
				...e,
				internals: {
					...e.internals,
					handleBounds: void 0
				}
			}), c = !0;
			continue;
		}
		let s = J(r.nodeElement), u = e.measured.width !== s.width || e.measured.height !== s.height;
		if (s.width && s.height && (u || !e.internals.handleBounds || r.force)) {
			let p = r.nodeElement.getBoundingClientRect(), m = co(e.extent) ? e.extent : a, { positionAbsolute: h } = e.internals;
			e.parentId && e.extent === "parent" ? h = Ba(h, s, t.get(e.parentId)) : m && (h = za(h, m, s));
			let g = {
				...e,
				measured: s,
				internals: {
					...e.internals,
					positionAbsolute: h,
					handleBounds: {
						source: So("source", r.nodeElement, p, d, e.id),
						target: So("target", r.nodeElement, p, d, e.id)
					}
				}
			};
			t.set(e.id, g), e.parentId && rs(g, t, n, {
				nodeOrigin: i,
				zIndexMode: o
			}), c = !0, u && (l.push({
				id: e.id,
				type: "dimensions",
				dimensions: s
			}), e.expandParent && e.parentId && f.push({
				id: e.id,
				parentId: e.parentId,
				rect: Ka(g, i)
			}));
		}
	}
	if (f.length > 0) {
		let e = os(f, t, n, i);
		l.push(...e);
	}
	return {
		changes: l,
		updatedInternals: c
	};
}
async function cs({ delta: e, panZoom: t, transform: n, translateExtent: r, width: i, height: a }) {
	if (!t || !e.x && !e.y) return !1;
	let o = await t.setViewportConstrained({
		x: n[0] + e.x,
		y: n[1] + e.y,
		zoom: n[2]
	}, [[0, 0], [i, a]], r);
	return !!o && (o.x !== n[0] || o.y !== n[1] || o.k !== n[2]);
}
function ls(e, t, n, r, i, a) {
	let o = i, s = r.get(o) || /* @__PURE__ */ new Map();
	r.set(o, s.set(n, t)), o = `${i}-${e}`;
	let c = r.get(o) || /* @__PURE__ */ new Map();
	if (r.set(o, c.set(n, t)), a) {
		o = `${i}-${e}-${a}`;
		let s = r.get(o) || /* @__PURE__ */ new Map();
		r.set(o, s.set(n, t));
	}
}
function us(e, t, n) {
	e.clear(), t.clear();
	for (let r of n) {
		let { source: n, target: i, sourceHandle: a = null, targetHandle: o = null } = r, s = {
			edgeId: r.id,
			source: n,
			target: i,
			sourceHandle: a,
			targetHandle: o
		}, c = `${n}-${a}--${i}-${o}`;
		ls("source", s, `${i}-${o}--${n}-${a}`, e, n, a), ls("target", s, c, e, i, o), t.set(r.id, r);
	}
}
function ds(e, t) {
	if (!e.parentId) return !1;
	let n = t.get(e.parentId);
	return n ? n.selected ? !0 : ds(n, t) : !1;
}
function fs(e, t, n) {
	let r = e;
	do {
		if (r?.matches?.(t)) return !0;
		if (r === n) return !1;
		r = r?.parentElement;
	} while (r);
	return !1;
}
function ps(e, t, n, r) {
	let i = /* @__PURE__ */ new Map();
	for (let [a, o] of e) if ((o.selected || o.id === r) && (!o.parentId || !ds(o, e)) && (o.draggable || t && o.draggable === void 0)) {
		let t = e.get(a);
		t && i.set(a, {
			id: a,
			position: t.position || {
				x: 0,
				y: 0
			},
			distance: {
				x: n.x - t.internals.positionAbsolute.x,
				y: n.y - t.internals.positionAbsolute.y
			},
			extent: t.extent,
			parentId: t.parentId,
			origin: t.origin,
			expandParent: t.expandParent,
			internals: { positionAbsolute: t.internals.positionAbsolute || {
				x: 0,
				y: 0
			} },
			measured: {
				width: t.measured.width ?? 0,
				height: t.measured.height ?? 0
			}
		});
	}
	return i;
}
function ms({ nodeId: e, dragItems: t, nodeLookup: n, dragging: r = !0 }) {
	let i = [];
	for (let [e, a] of t) {
		let t = n.get(e)?.internals.userNode;
		t && i.push({
			...t,
			position: a.position,
			dragging: r
		});
	}
	if (!e) return [i[0], i];
	let a = n.get(e)?.internals.userNode;
	return [a ? {
		...a,
		position: t.get(e)?.position || a.position,
		dragging: r
	} : i[0], i];
}
function hs({ dragItems: e, snapGrid: t, x: n, y: r }) {
	let i = e.values().next().value;
	if (!i) return null;
	let a = {
		x: n - i.distance.x,
		y: r - i.distance.y
	}, o = eo(a, t);
	return {
		x: o.x - a.x,
		y: o.y - a.y
	};
}
function gs({ onNodeMouseDown: e, getStoreItems: t, onDragStart: n, onDrag: r, onDragStop: i }) {
	let a = {
		x: null,
		y: null
	}, o = 0, s = /* @__PURE__ */ new Map(), c = !1, l = {
		x: 0,
		y: 0
	}, u = null, d = !1, f = null, p = !1, m = !1, h = null;
	function g({ noDragClassName: g, handleSelector: _, domNode: v, isSelectable: y, nodeId: b, nodeClickDistance: x = 0 }) {
		f = Bt(v);
		function S({ x: e, y: n }) {
			let { nodeLookup: i, nodeExtent: o, snapGrid: c, snapToGrid: l, nodeOrigin: u, onNodeDrag: d, onSelectionDrag: f, onError: p, updateNodePositions: g } = t();
			a = {
				x: e,
				y: n
			};
			let _ = !1, v = s.size > 1, y = v && o ? Wa(ja(s)) : null, x = v && l ? hs({
				dragItems: s,
				snapGrid: c,
				x: e,
				y: n
			}) : null;
			for (let [t, r] of s) {
				if (!i.has(t)) continue;
				let a = {
					x: e - r.distance.x,
					y: n - r.distance.y
				};
				l && (a = x ? {
					x: Math.round(a.x + x.x),
					y: Math.round(a.y + x.y)
				} : eo(a, c));
				let s = null;
				if (v && o && !r.extent && y) {
					let { positionAbsolute: e } = r.internals, t = e.x - y.x + o[0][0], n = e.x + r.measured.width - y.x2 + o[1][0], i = e.y - y.y + o[0][1], a = e.y + r.measured.height - y.y2 + o[1][1];
					s = [[t, i], [n, a]];
				}
				let { position: d, positionAbsolute: f } = Ia({
					nodeId: t,
					nextPosition: a,
					nodeLookup: i,
					nodeExtent: s || o,
					nodeOrigin: u,
					onError: p
				});
				_ = _ || r.position.x !== d.x || r.position.y !== d.y, r.position = d, r.internals.positionAbsolute = f;
			}
			if (m ||= _, _ && (g(s, !0), h && (r || d || !b && f))) {
				let [e, t] = ms({
					nodeId: b,
					dragItems: s,
					nodeLookup: i
				});
				r?.(h, s, e, t), d?.(h, e, t), b || f?.(h, t);
			}
		}
		async function C() {
			if (!u) return;
			let { transform: e, panBy: n, autoPanSpeed: r, autoPanOnNodeDrag: i } = t();
			if (!i) {
				c = !1, cancelAnimationFrame(o);
				return;
			}
			let [s, d] = Ha(l, u, r);
			(s !== 0 || d !== 0) && (a.x = (a.x ?? 0) - s / e[2], a.y = (a.y ?? 0) - d / e[2], await n({
				x: s,
				y: d
			}) && S(a)), o = requestAnimationFrame(C);
		}
		function w(r) {
			let { nodeLookup: i, multiSelectionActive: o, nodesDraggable: c, transform: l, snapGrid: f, snapToGrid: p, selectNodesOnDrag: m, onNodeDragStart: h, onSelectionDragStart: g, unselectNodesAndEdges: _ } = t();
			d = !0, (!m || !y) && !o && b && (i.get(b)?.selected || _()), y && m && b && e?.(b);
			let v = go(r.sourceEvent, {
				transform: l,
				snapGrid: f,
				snapToGrid: p,
				containerBounds: u
			});
			if (a = v, s = ps(i, c, v, b), s.size > 0 && (n || h || !b && g)) {
				let [e, t] = ms({
					nodeId: b,
					dragItems: s,
					nodeLookup: i
				});
				n?.(r.sourceEvent, s, e, t), h?.(r.sourceEvent, e, t), b || g?.(r.sourceEvent, t);
			}
		}
		let T = en().clickDistance(x).on("start", (e) => {
			let { domNode: n, nodeDragThreshold: r, transform: i, snapGrid: o, snapToGrid: s } = t();
			u = n?.getBoundingClientRect() || null, p = !1, m = !1, h = e.sourceEvent, r === 0 && w(e), a = go(e.sourceEvent, {
				transform: i,
				snapGrid: o,
				snapToGrid: s,
				containerBounds: u
			}), l = xo(e.sourceEvent, u);
		}).on("drag", (e) => {
			let { autoPanOnNodeDrag: n, transform: r, snapGrid: i, snapToGrid: o, nodeDragThreshold: f, nodeLookup: m } = t(), g = go(e.sourceEvent, {
				transform: r,
				snapGrid: i,
				snapToGrid: o,
				containerBounds: u
			});
			if (h = e.sourceEvent, (e.sourceEvent.type === "touchmove" && e.sourceEvent.touches.length > 1 || b && !m.has(b)) && (p = !0), !p) {
				if (!c && n && d && (c = !0, C()), !d) {
					let t = xo(e.sourceEvent, u), n = t.x - l.x, r = t.y - l.y;
					Math.sqrt(n * n + r * r) > f && w(e);
				}
				(a.x !== g.xSnapped || a.y !== g.ySnapped) && s && d && (l = xo(e.sourceEvent, u), S(g));
			}
		}).on("end", (e) => {
			if (!d || p) {
				p && s.size > 0 && t().updateNodePositions(s, !1);
				return;
			}
			if (c = !1, d = !1, cancelAnimationFrame(o), s.size > 0) {
				let { nodeLookup: n, updateNodePositions: r, onNodeDragStop: a, onSelectionDragStop: o } = t();
				if (m &&= (r(s, !1), !1), i || a || !b && o) {
					let [t, r] = ms({
						nodeId: b,
						dragItems: s,
						nodeLookup: n,
						dragging: !1
					});
					i?.(e.sourceEvent, s, t, r), a?.(e.sourceEvent, t, r), b || o?.(e.sourceEvent, r);
				}
			}
		}).filter((e) => {
			let t = e.target;
			return !e.button && (!g || !fs(t, `.${g}`, v)) && (!_ || fs(t, _, v));
		});
		f.call(T);
	}
	function _() {
		f?.on(".drag", null);
	}
	return {
		update: g,
		destroy: _
	};
}
function _s(e, t, n) {
	let r = [], i = {
		x: e.x - n,
		y: e.y - n,
		width: n * 2,
		height: n * 2
	};
	for (let e of t.values()) Xa(i, Ka(e)) > 0 && r.push(e);
	return r;
}
var vs = 250;
function ys(e, t, n, r) {
	let i = [], a = Infinity, o = _s(e, n, t + vs);
	for (let n of o) {
		let o = [...n.internals.handleBounds?.source ?? [], ...n.internals.handleBounds?.target ?? []];
		for (let s of o) {
			if (r.nodeId === s.nodeId && r.type === s.type && r.id === s.id) continue;
			let { x: o, y: c } = Uo(n, s, s.position, !0), l = Math.sqrt((o - e.x) ** 2 + (c - e.y) ** 2);
			l > t || (l < a ? (i = [{
				...s,
				x: o,
				y: c
			}], a = l) : l === a && i.push({
				...s,
				x: o,
				y: c
			}));
		}
	}
	if (!i.length) return null;
	if (i.length > 1) {
		let e = r.type === "source" ? "target" : "source";
		return i.find((t) => t.type === e) ?? i[0];
	}
	return i[0];
}
function bs(e, t, n, r, i, a = !1) {
	let o = r.get(e);
	if (!o) return null;
	let s = i === "strict" ? o.internals.handleBounds?.[t] : [...o.internals.handleBounds?.source ?? [], ...o.internals.handleBounds?.target ?? []], c = (n ? s?.find((e) => e.id === n) : s?.[0]) ?? null;
	return c && a ? {
		...c,
		...Uo(o, c, c.position, !0)
	} : c;
}
function xs(e, t) {
	return e || (t?.classList.contains("target") ? "target" : t?.classList.contains("source") ? "source" : null);
}
function Ss(e, t) {
	let n = null;
	return t ? n = !0 : e && !t && (n = !1), n;
}
var Cs = () => !0;
function ws(e, { connectionMode: t, connectionRadius: n, handleId: r, nodeId: i, edgeUpdaterType: a, isTarget: o, domNode: s, nodeLookup: c, lib: l, autoPanOnConnect: u, flowId: d, panBy: f, cancelConnection: p, onConnectStart: m, onConnect: h, onConnectEnd: g, isValidConnection: _ = Cs, onReconnectEnd: v, updateConnection: y, getTransform: b, getFromHandle: x, autoPanSpeed: S, dragThreshold: C = 1, handleDomNode: w }) {
	let T = _o(e.target), E = 0, D, { x: O, y: k } = xo(e), A = xs(a, w), j = s?.getBoundingClientRect(), M = !1;
	if (!j || !A) return;
	let N = bs(i, A, r, c, t);
	if (!N) return;
	let P = xo(e, j), F = !1, I = null, ee = !1, L = null;
	function R() {
		if (!u || !j) return;
		let [e, t] = Ha(P, j, S);
		f({
			x: e,
			y: t
		}), E = requestAnimationFrame(R);
	}
	let z = {
		...N,
		nodeId: i,
		type: A,
		position: N.position
	}, B = c.get(i), te = {
		inProgress: !0,
		isValid: null,
		from: Uo(B, z, q.Left, !0),
		fromHandle: z,
		fromPosition: z.position,
		fromNode: B,
		to: P,
		toHandle: null,
		toPosition: wa[z.position],
		toNode: null,
		pointer: P
	};
	function ne() {
		M = !0, y(te), m?.(e, {
			nodeId: i,
			handleId: r,
			handleType: A
		});
	}
	C === 0 && ne();
	function re(e) {
		if (!M) {
			let { x: t, y: n } = xo(e), r = t - O, i = n - k;
			if (!(r * r + i * i > C * C)) return;
			ne();
		}
		if (!x() || !z) {
			ie(e);
			return;
		}
		let a = b();
		P = xo(e, j), D = ys(to(P, a, !1, [1, 1]), n, c, z), F ||= (R(), !0);
		let s = Ts(e, {
			handle: D,
			connectionMode: t,
			fromNodeId: i,
			fromHandleId: r,
			fromType: o ? "target" : "source",
			isValidConnection: _,
			doc: T,
			lib: l,
			flowId: d,
			nodeLookup: c
		});
		L = s.handleDomNode, I = s.connection, ee = Ss(!!D, s.isValid);
		let u = c.get(i), f = u ? Uo(u, z, q.Left, !0) : te.from, p = {
			...te,
			from: f,
			isValid: ee,
			to: s.toHandle && ee ? no({
				x: s.toHandle.x,
				y: s.toHandle.y
			}, a) : P,
			toHandle: s.toHandle,
			toPosition: ee && s.toHandle ? s.toHandle.position : wa[z.position],
			toNode: s.toHandle ? c.get(s.toHandle.nodeId) : null,
			pointer: P
		};
		y(p), te = p;
	}
	function ie(e) {
		if (!("touches" in e && e.touches.length > 0)) {
			if (M) {
				(D || L) && I && ee && h?.(I);
				let { inProgress: t, ...n } = te, r = {
					...n,
					toPosition: te.toHandle ? te.toPosition : null
				};
				g?.(e, r), a && v?.(e, r);
			}
			p(), cancelAnimationFrame(E), F = !1, ee = !1, I = null, L = null, T.removeEventListener("mousemove", re), T.removeEventListener("mouseup", ie), T.removeEventListener("touchmove", re), T.removeEventListener("touchend", ie);
		}
	}
	T.addEventListener("mousemove", re), T.addEventListener("mouseup", ie), T.addEventListener("touchmove", re), T.addEventListener("touchend", ie);
}
function Ts(e, { handle: t, connectionMode: n, fromNodeId: r, fromHandleId: i, fromType: a, doc: o, lib: s, flowId: c, isValidConnection: l = Cs, nodeLookup: u }) {
	let d = a === "target", f = t ? o.querySelector(`.${s}-flow__handle[data-id="${c}-${t?.nodeId}-${t?.id}-${t?.type}"]`) : null, { x: p, y: m } = xo(e), h = o.elementFromPoint(p, m), g = h?.classList.contains(`${s}-flow__handle`) ? h : f, _ = {
		handleDomNode: g,
		isValid: !1,
		connection: null,
		toHandle: null
	};
	if (g) {
		let e = xs(void 0, g), t = g.getAttribute("data-nodeid"), a = g.getAttribute("data-handleid"), o = g.classList.contains("connectable"), s = g.classList.contains("connectableend");
		if (!t || !e) return _;
		let c = {
			source: d ? t : r,
			sourceHandle: d ? a : i,
			target: d ? r : t,
			targetHandle: d ? i : a
		};
		_.connection = c, _.isValid = o && s && (n === ya.Strict ? d && e === "source" || !d && e === "target" : t !== r || a !== i) && l(c), _.toHandle = bs(t, e, a, u, n, !0);
	}
	return _;
}
var Es = {
	onPointerDown: ws,
	isValid: Ts
};
function Ds({ domNode: e, panZoom: t, getTransform: n, getViewScale: r }) {
	let i = Bt(e);
	function a({ translateExtent: e, width: a, height: o, zoomStep: s = 1, pannable: c = !0, zoomable: l = !0, inversePan: u = !1 }) {
		let d = (e) => {
			if (e.sourceEvent.type !== "wheel" || !t) return;
			let r = n(), i = e.sourceEvent.ctrlKey && so() ? 10 : 1, a = -e.sourceEvent.deltaY * (e.sourceEvent.deltaMode === 1 ? .05 : e.sourceEvent.deltaMode ? 1 : .002) * s, o = r[2] * 2 ** (a * i);
			t.scaleTo(o);
		}, f = [0, 0], p = ma().on("start", (e) => {
			(e.sourceEvent.type === "mousedown" || e.sourceEvent.type === "touchstart") && (f = [e.sourceEvent.clientX ?? e.sourceEvent.touches[0].clientX, e.sourceEvent.clientY ?? e.sourceEvent.touches[0].clientY]);
		}).on("zoom", c ? (i) => {
			let s = n();
			if (i.sourceEvent.type !== "mousemove" && i.sourceEvent.type !== "touchmove" || !t) return;
			let c = [i.sourceEvent.clientX ?? i.sourceEvent.touches[0].clientX, i.sourceEvent.clientY ?? i.sourceEvent.touches[0].clientY], l = [c[0] - f[0], c[1] - f[1]];
			f = c;
			let d = r() * Math.max(s[2], Math.log(s[2])) * (u ? -1 : 1), p = {
				x: s[0] - l[0] * d,
				y: s[1] - l[1] * d
			}, m = [[0, 0], [a, o]];
			t.setViewportConstrained({
				x: p.x,
				y: p.y,
				zoom: s[2]
			}, m, e);
		} : null).on("zoom.wheel", l ? d : null);
		i.call(p, {});
	}
	function o() {
		i.on("zoom", null);
	}
	return {
		update: a,
		destroy: o,
		pointer: Vt
	};
}
var Os = (e) => ({
	x: e.x,
	y: e.y,
	zoom: e.k
}), ks = ({ x: e, y: t, zoom: n }) => ia.translate(e, t).scale(n), As = (e, t) => e.target.closest(`.${t}`), js = (e, t) => t === 2 && Array.isArray(e) && e.includes(2), Ms = (e) => ((e *= 2) <= 1 ? e * e * e : (e -= 2) * e * e + 2) / 2, Ns = (e, t = 0, n = Ms, r = () => {}) => {
	let i = typeof t == "number" && t > 0;
	return i || r(), i ? e.transition().duration(t).ease(n).on("end", r) : e;
}, Ps = (e) => {
	let t = e.ctrlKey && so() ? 10 : 1;
	return -e.deltaY * (e.deltaMode === 1 ? .05 : e.deltaMode ? 1 : .002) * t;
};
function Fs({ zoomPanValues: e, noWheelClassName: t, d3Selection: n, d3Zoom: r, panOnScrollMode: i, panOnScrollSpeed: a, zoomOnPinch: o, onPanZoomStart: s, onPanZoom: c, onPanZoomEnd: l }) {
	return (u) => {
		if (As(u, t)) return u.ctrlKey && u.preventDefault(), !1;
		u.preventDefault(), u.stopImmediatePropagation();
		let d = n.property("__zoom").k || 1;
		if (u.ctrlKey && o) {
			let e = Vt(u), t = d * 2 ** Ps(u);
			r.scaleTo(n, t, e, u);
			return;
		}
		let f = u.deltaMode === 1 ? 20 : 1, p = i === ba.Vertical ? 0 : u.deltaX * f, m = i === ba.Horizontal ? 0 : u.deltaY * f;
		!so() && u.shiftKey && i !== ba.Vertical && (p = u.deltaY * f, m = 0), r.translateBy(n, -(p / d) * a, -(m / d) * a, { internal: !0 });
		let h = Os(n.property("__zoom"));
		clearTimeout(e.panScrollTimeout), e.isPanScrolling ? (c?.(u, h), e.panScrollTimeout = setTimeout(() => {
			l?.(u, h), e.isPanScrolling = !1;
		}, 150)) : (e.isPanScrolling = !0, s?.(u, h));
	};
}
function Is({ noWheelClassName: e, preventScrolling: t, d3ZoomHandler: n }) {
	return function(r, i) {
		let a = r.type === "wheel", o = !t && a && !r.ctrlKey, s = As(r, e);
		if (r.ctrlKey && a && s && r.preventDefault(), o || s) return null;
		r.preventDefault(), n.call(this, r, i);
	};
}
function Ls({ zoomPanValues: e, onDraggingChange: t, onPanZoomStart: n }) {
	return (r) => {
		if (r.sourceEvent?.internal) return;
		let i = Os(r.transform);
		e.mouseButton = r.sourceEvent?.button || 0, e.isZoomingOrPanning = !0, e.prevViewport = i, r.sourceEvent?.type === "mousedown" && t(!0), n && n?.(r.sourceEvent, i);
	};
}
function Rs({ zoomPanValues: e, panOnDrag: t, onPaneContextMenu: n, onTransformChange: r, onPanZoom: i }) {
	return (a) => {
		e.usedRightMouseButton = !!(n && js(t, e.mouseButton ?? 0)), a.sourceEvent?.sync || r([
			a.transform.x,
			a.transform.y,
			a.transform.k
		]), i && !a.sourceEvent?.internal && i?.(a.sourceEvent, Os(a.transform));
	};
}
function zs({ zoomPanValues: e, panOnDrag: t, panOnScroll: n, onDraggingChange: r, onPanZoomEnd: i, onPaneContextMenu: a }) {
	return (o) => {
		if (!o.sourceEvent?.internal && (e.isZoomingOrPanning = !1, a && js(t, e.mouseButton ?? 0) && !e.usedRightMouseButton && o.sourceEvent && a(o.sourceEvent), e.usedRightMouseButton = !1, r(!1), i)) {
			let t = Os(o.transform);
			e.prevViewport = t, clearTimeout(e.timerId), e.timerId = setTimeout(() => {
				i?.(o.sourceEvent, t);
			}, n ? 150 : 0);
		}
	};
}
function Bs({ zoomActivationKeyPressed: e, zoomOnScroll: t, zoomOnPinch: n, panOnDrag: r, panOnScroll: i, zoomOnDoubleClick: a, userSelectionActive: o, noWheelClassName: s, noPanClassName: c, lib: l, connectionInProgress: u }) {
	return (d) => {
		let f = e || t, p = n && d.ctrlKey, m = d.type === "wheel";
		if (d.button === 1 && d.type === "mousedown" && (As(d, `${l}-flow__node`) || As(d, `${l}-flow__edge`))) return !0;
		if (!r && !f && !i && !a && !n || o || u && !m || As(d, s) && m || As(d, c) && (!m || i && m && !e) || !n && d.ctrlKey && m) return !1;
		if (!n && d.type === "touchstart" && d.touches?.length > 1) return d.preventDefault(), !1;
		if (!f && !i && !p && m || !r && (d.type === "mousedown" || d.type === "touchstart") || Array.isArray(r) && !r.includes(d.button) && d.type === "mousedown") return !1;
		let h = Array.isArray(r) && r.includes(d.button) || !d.button || d.button <= 1;
		return (!d.ctrlKey || m) && h;
	};
}
function Vs({ domNode: e, minZoom: t, maxZoom: n, translateExtent: r, viewport: i, onPanZoom: a, onPanZoomStart: o, onPanZoomEnd: s, onDraggingChange: c }) {
	let l = {
		isZoomingOrPanning: !1,
		usedRightMouseButton: !1,
		prevViewport: {},
		mouseButton: 0,
		timerId: void 0,
		panScrollTimeout: void 0,
		isPanScrolling: !1
	}, u = e.getBoundingClientRect(), d = ma().scaleExtent([t, n]).translateExtent(r), f = Bt(e).call(d);
	v({
		x: i.x,
		y: i.y,
		zoom: Ra(i.zoom, t, n)
	}, [[0, 0], [u.width, u.height]], r);
	let p = f.on("wheel.zoom"), m = f.on("dblclick.zoom");
	d.wheelDelta(Ps);
	async function h(e, t) {
		return f ? new Promise((n) => {
			d?.interpolate(t?.interpolate === "linear" ? rr : _r).transform(Ns(f, t?.duration, t?.ease, () => n(!0)), e);
		}) : !1;
	}
	function g({ noWheelClassName: e, noPanClassName: t, onPaneContextMenu: n, userSelectionActive: r, panOnScroll: i, panOnDrag: u, panOnScrollMode: h, panOnScrollSpeed: g, preventScrolling: v, zoomOnPinch: y, zoomOnScroll: b, zoomOnDoubleClick: x, zoomActivationKeyPressed: S, lib: C, onTransformChange: w, connectionInProgress: T, paneClickDistance: E, selectionOnDrag: D }) {
		r && !l.isZoomingOrPanning && _();
		let O = i && !S && !r;
		d.clickDistance(D ? Infinity : !Qa(E) || E < 0 ? 0 : E);
		let k = O ? Fs({
			zoomPanValues: l,
			noWheelClassName: e,
			d3Selection: f,
			d3Zoom: d,
			panOnScrollMode: h,
			panOnScrollSpeed: g,
			zoomOnPinch: y,
			onPanZoomStart: o,
			onPanZoom: a,
			onPanZoomEnd: s
		}) : Is({
			noWheelClassName: e,
			preventScrolling: v,
			d3ZoomHandler: p
		});
		f.on("wheel.zoom", k, { passive: !1 });
		let A = Ls({
			zoomPanValues: l,
			onDraggingChange: c,
			onPanZoomStart: o
		});
		d.on("start", A);
		let j = Rs({
			zoomPanValues: l,
			panOnDrag: u,
			onPaneContextMenu: !!n,
			onPanZoom: a,
			onTransformChange: w
		});
		d.on("zoom", j);
		let M = zs({
			zoomPanValues: l,
			panOnDrag: u,
			panOnScroll: i,
			onPaneContextMenu: n,
			onPanZoomEnd: s,
			onDraggingChange: c
		});
		d.on("end", M);
		let N = Bs({
			zoomActivationKeyPressed: S,
			panOnDrag: u,
			zoomOnScroll: b,
			panOnScroll: i,
			zoomOnDoubleClick: x,
			zoomOnPinch: y,
			userSelectionActive: r,
			noPanClassName: t,
			noWheelClassName: e,
			lib: C,
			connectionInProgress: T
		});
		d.filter(N), x ? f.on("dblclick.zoom", m) : f.on("dblclick.zoom", null);
	}
	function _() {
		d.on("zoom", null);
	}
	async function v(e, t, n) {
		let r = ks(e), i = d?.constrain()(r, t, n);
		return i && await h(i), i;
	}
	async function y(e, t) {
		let n = ks(e);
		return await h(n, t), n;
	}
	function b(e) {
		if (f) {
			let t = ks(e), n = f.property("__zoom");
			(n.k !== e.zoom || n.x !== e.x || n.y !== e.y) && d?.transform(f, t, null, { sync: !0 });
		}
	}
	function x() {
		let e = f ? aa(f.node()) : {
			x: 0,
			y: 0,
			k: 1
		};
		return {
			x: e.x,
			y: e.y,
			zoom: e.k
		};
	}
	async function S(e, t) {
		return f ? new Promise((n) => {
			d?.interpolate(t?.interpolate === "linear" ? rr : _r).scaleTo(Ns(f, t?.duration, t?.ease, () => n(!0)), e);
		}) : !1;
	}
	async function C(e, t) {
		return f ? new Promise((n) => {
			d?.interpolate(t?.interpolate === "linear" ? rr : _r).scaleBy(Ns(f, t?.duration, t?.ease, () => n(!0)), e);
		}) : !1;
	}
	function w(e) {
		d?.scaleExtent(e);
	}
	function T(e) {
		d?.translateExtent(e);
	}
	function E(e) {
		let t = !Qa(e) || e < 0 ? 0 : e;
		d?.clickDistance(t);
	}
	return {
		update: g,
		destroy: _,
		setViewport: y,
		setViewportConstrained: v,
		getViewport: x,
		scaleTo: S,
		scaleBy: C,
		setScaleExtent: w,
		setTranslateExtent: T,
		syncViewport: b,
		setClickDistance: E
	};
}
var Hs;
(function(e) {
	e.Line = "line", e.Handle = "handle";
})(Hs ||= {});
function Us({ width: e, prevWidth: t, height: n, prevHeight: r, affectsX: i, affectsY: a }) {
	let o = e - t, s = n - r, c = [o > 0 ? 1 : o < 0 ? -1 : 0, s > 0 ? 1 : s < 0 ? -1 : 0];
	return o && i && (c[0] *= -1), s && a && (c[1] *= -1), c;
}
function Ws(e) {
	return {
		isHorizontal: e.includes("right") || e.includes("left"),
		isVertical: e.includes("bottom") || e.includes("top"),
		affectsX: e.includes("left"),
		affectsY: e.includes("top")
	};
}
function Gs(e, t) {
	return Math.max(0, t - e);
}
function Ks(e, t) {
	return Math.max(0, e - t);
}
function qs(e, t, n) {
	return Math.max(0, t - e, e - n);
}
function Js(e, t) {
	return e ? !t : t;
}
function Ys(e, t, n, r, i, a, o, s) {
	let { affectsX: c, affectsY: l } = t, { isHorizontal: u, isVertical: d } = t, f = u && d, { xSnapped: p, ySnapped: m } = n, { minWidth: h, maxWidth: g, minHeight: _, maxHeight: v } = r, { x: y, y: b, width: x, height: S, aspectRatio: C } = e, w = Math.floor(u ? p - e.pointerX : 0), T = Math.floor(d ? m - e.pointerY : 0), E = x + (c ? -w : w), D = S + (l ? -T : T), O = -a[0] * x, k = -a[1] * S, A = qs(E, h, g), j = qs(D, _, v);
	if (o) {
		let e = 0, t = 0;
		c && w < 0 ? e = Gs(y + w + O, o[0][0]) : !c && w > 0 && (e = Ks(y + E + O, o[1][0])), l && T < 0 ? t = Gs(b + T + k, o[0][1]) : !l && T > 0 && (t = Ks(b + D + k, o[1][1])), A = Math.max(A, e), j = Math.max(j, t);
	}
	if (s) {
		let e = 0, t = 0;
		c && w > 0 ? e = Ks(y + w, s[0][0]) : !c && w < 0 && (e = Gs(y + E, s[1][0])), l && T > 0 ? t = Ks(b + T, s[0][1]) : !l && T < 0 && (t = Gs(b + D, s[1][1])), A = Math.max(A, e), j = Math.max(j, t);
	}
	if (i) {
		if (u) {
			let e = qs(E / C, _, v) * C;
			if (A = Math.max(A, e), o) {
				let e = 0;
				e = !c && !l || c && !l && f ? Ks(b + k + E / C, o[1][1]) * C : Gs(b + k + (c ? w : -w) / C, o[0][1]) * C, A = Math.max(A, e);
			}
			if (s) {
				let e = 0;
				e = !c && !l || c && !l && f ? Gs(b + E / C, s[1][1]) * C : Ks(b + (c ? w : -w) / C, s[0][1]) * C, A = Math.max(A, e);
			}
		}
		if (d) {
			let e = qs(D * C, h, g) / C;
			if (j = Math.max(j, e), o) {
				let e = 0;
				e = !c && !l || l && !c && f ? Ks(y + D * C + O, o[1][0]) / C : Gs(y + (l ? T : -T) * C + O, o[0][0]) / C, j = Math.max(j, e);
			}
			if (s) {
				let e = 0;
				e = !c && !l || l && !c && f ? Gs(y + D * C, s[1][0]) / C : Ks(y + (l ? T : -T) * C, s[0][0]) / C, j = Math.max(j, e);
			}
		}
	}
	T += T < 0 ? j : -j, w += w < 0 ? A : -A, i && (f ? E > D * C ? T = (Js(c, l) ? -w : w) / C : w = (Js(c, l) ? -T : T) * C : u ? (T = w / C, l = c) : (w = T * C, c = l));
	let M = c ? y + w : y, N = l ? b + T : b;
	return {
		width: x + (c ? -w : w),
		height: S + (l ? -T : T),
		x: a[0] * w * (c ? -1 : 1) + M,
		y: a[1] * T * (l ? -1 : 1) + N
	};
}
var Xs = {
	width: 0,
	height: 0,
	x: 0,
	y: 0
}, Zs = {
	...Xs,
	pointerX: 0,
	pointerY: 0,
	aspectRatio: 1
};
function Qs(e, t, n) {
	let r = t.position.x + e.position.x, i = t.position.y + e.position.y, a = e.measured.width ?? 0, o = e.measured.height ?? 0, s = n[0] * a, c = n[1] * o;
	return [[r - s, i - c], [r + a - s, i + o - c]];
}
function $s({ domNode: e, nodeId: t, getStoreItems: n, onChange: r, onEnd: i }) {
	let a = Bt(e), o = {
		controlDirection: Ws("bottom-right"),
		boundaries: {
			minWidth: 0,
			minHeight: 0,
			maxWidth: Number.MAX_VALUE,
			maxHeight: Number.MAX_VALUE
		},
		resizeDirection: void 0,
		keepAspectRatio: !1
	};
	function s({ controlPosition: e, boundaries: s, keepAspectRatio: c, resizeDirection: l, onResizeStart: u, onResize: d, onResizeEnd: f, shouldResize: p }) {
		let m = { ...Xs }, h = { ...Zs };
		o = {
			boundaries: s,
			resizeDirection: l,
			keepAspectRatio: c,
			controlDirection: Ws(e)
		};
		let g, _ = null, v = [], y, b, x, S = !1, C = en().on("start", (e) => {
			let { nodeLookup: r, transform: i, snapGrid: a, snapToGrid: o, nodeOrigin: s, paneDomNode: c } = n();
			if (g = r.get(t), !g) return;
			_ = c?.getBoundingClientRect() ?? null;
			let { xSnapped: l, ySnapped: d } = go(e.sourceEvent, {
				transform: i,
				snapGrid: a,
				snapToGrid: o,
				containerBounds: _
			});
			m = {
				width: g.measured.width ?? 0,
				height: g.measured.height ?? 0,
				x: g.position.x ?? 0,
				y: g.position.y ?? 0
			}, h = {
				...m,
				pointerX: l,
				pointerY: d,
				aspectRatio: m.width / m.height
			}, y = void 0, b = co(g.extent) ? g.extent : void 0, g.parentId && (g.extent === "parent" || g.expandParent) && (y = r.get(g.parentId)), y && g.extent === "parent" && (b = [[0, 0], [y.measured.width, y.measured.height]]), v = [], x = void 0;
			for (let [e, n] of r) if (n.parentId === t && (v.push({
				id: e,
				position: { ...n.position },
				extent: n.extent
			}), n.extent === "parent" || n.expandParent)) {
				let e = Qs(n, g, n.origin ?? s);
				x = x ? [[Math.min(e[0][0], x[0][0]), Math.min(e[0][1], x[0][1])], [Math.max(e[1][0], x[1][0]), Math.max(e[1][1], x[1][1])]] : e;
			}
			u?.(e, { ...m });
		}).on("drag", (e) => {
			let { transform: t, snapGrid: i, snapToGrid: a, nodeOrigin: s } = n(), c = go(e.sourceEvent, {
				transform: t,
				snapGrid: i,
				snapToGrid: a,
				containerBounds: _
			}), l = [];
			if (!g) return;
			let { x: u, y: f, width: C, height: w } = m, T = {}, E = g.origin ?? s, { width: D, height: O, x: k, y: A } = Ys(h, o.controlDirection, c, o.boundaries, o.keepAspectRatio, E, b, x), j = D !== C, M = O !== w, N = k !== u && j, P = A !== f && M;
			if (!N && !P && !j && !M) return;
			if ((N || P || E[0] === 1 || E[1] === 1) && (T.x = N ? k : m.x, T.y = P ? A : m.y, m.x = T.x, m.y = T.y, v.length > 0)) {
				let e = k - u, t = A - f;
				for (let n of v) n.position = {
					x: n.position.x - e + E[0] * (D - C),
					y: n.position.y - t + E[1] * (O - w)
				}, l.push(n);
			}
			if ((j || M) && (T.width = j && (!o.resizeDirection || o.resizeDirection === "horizontal") ? D : m.width, T.height = M && (!o.resizeDirection || o.resizeDirection === "vertical") ? O : m.height, m.width = T.width, m.height = T.height), y && g.expandParent) {
				let e = E[0] * (T.width ?? 0);
				T.x && T.x < e && (m.x = e, h.x -= T.x - e);
				let t = E[1] * (T.height ?? 0);
				T.y && T.y < t && (m.y = t, h.y -= T.y - t);
			}
			let F = Us({
				width: m.width,
				prevWidth: C,
				height: m.height,
				prevHeight: w,
				affectsX: o.controlDirection.affectsX,
				affectsY: o.controlDirection.affectsY
			}), I = {
				...m,
				direction: F
			};
			p?.(e, I) !== !1 && (S = !0, d?.(e, I), r(T, l));
		}).on("end", (e) => {
			S &&= (f?.(e, { ...m }), i?.({ ...m }), !1);
		});
		a.call(C);
	}
	function c() {
		a.on(".drag", null);
	}
	return {
		update: s,
		destroy: c
	};
}
//#endregion
//#region node_modules/use-sync-external-store/cjs/use-sync-external-store-shim.production.js
var ec = /* @__PURE__ */ o(((e) => {
	var t = u();
	function n(e, t) {
		return e === t && (e !== 0 || 1 / e == 1 / t) || e !== e && t !== t;
	}
	var r = typeof Object.is == "function" ? Object.is : n, i = t.useState, a = t.useEffect, o = t.useLayoutEffect, s = t.useDebugValue;
	function c(e, t) {
		var n = t(), r = i({ inst: {
			value: n,
			getSnapshot: t
		} }), c = r[0].inst, u = r[1];
		return o(function() {
			c.value = n, c.getSnapshot = t, l(c) && u({ inst: c });
		}, [
			e,
			n,
			t
		]), a(function() {
			return l(c) && u({ inst: c }), e(function() {
				l(c) && u({ inst: c });
			});
		}, [e]), s(n), n;
	}
	function l(e) {
		var t = e.getSnapshot;
		e = e.value;
		try {
			var n = t();
			return !r(e, n);
		} catch {
			return !0;
		}
	}
	function d(e, t) {
		return t();
	}
	var f = typeof window > "u" || window.document === void 0 || window.document.createElement === void 0 ? d : c;
	e.useSyncExternalStore = t.useSyncExternalStore === void 0 ? f : t.useSyncExternalStore;
})), tc = /* @__PURE__ */ o(((e, t) => {
	t.exports = ec();
})), nc = /* @__PURE__ */ o(((e) => {
	var t = u(), n = tc();
	function r(e, t) {
		return e === t && (e !== 0 || 1 / e == 1 / t) || e !== e && t !== t;
	}
	var i = typeof Object.is == "function" ? Object.is : r, a = n.useSyncExternalStore, o = t.useRef, s = t.useEffect, c = t.useMemo, l = t.useDebugValue;
	e.useSyncExternalStoreWithSelector = function(e, t, n, r, u) {
		var d = o(null);
		if (d.current === null) {
			var f = {
				hasValue: !1,
				value: null
			};
			d.current = f;
		} else f = d.current;
		d = c(function() {
			function e(e) {
				if (!a) {
					if (a = !0, o = e, e = r(e), u !== void 0 && f.hasValue) {
						var t = f.value;
						if (u(t, e)) return s = t;
					}
					return s = e;
				}
				if (t = s, i(o, e)) return t;
				var n = r(e);
				return u !== void 0 && u(t, n) ? (o = e, t) : (o = e, s = n);
			}
			var a = !1, o, s, c = n === void 0 ? null : n;
			return [function() {
				return e(t());
			}, c === null ? void 0 : function() {
				return e(c());
			}];
		}, [
			t,
			n,
			r,
			u
		]);
		var p = a(e, d[0], d[1]);
		return s(function() {
			f.hasValue = !0, f.value = p;
		}, [p]), l(p), p;
	};
})), rc = /* @__PURE__ */ c((/* @__PURE__ */ o(((e, t) => {
	t.exports = nc();
})))(), 1), ic = (e) => {
	let t, n = /* @__PURE__ */ new Set(), r = (e, r) => {
		let i = typeof e == "function" ? e(t) : e;
		if (!Object.is(i, t)) {
			let e = t;
			t = r ?? (typeof i != "object" || !i) ? i : Object.assign({}, t, i), n.forEach((n) => n(t, e));
		}
	}, i = () => t, a = {
		setState: r,
		getState: i,
		getInitialState: () => o,
		subscribe: (e) => (n.add(e), () => n.delete(e)),
		destroy: () => {
			n.clear();
		}
	}, o = t = e(r, i, a);
	return a;
}, ac = (e) => e ? ic(e) : ic, { useDebugValue: oc } = b.default, { useSyncExternalStoreWithSelector: sc } = rc.default, cc = (e) => e;
function lc(e, t = cc, n) {
	let r = sc(e.subscribe, e.getState, e.getServerState || e.getInitialState, t, n);
	return oc(r), r;
}
var uc = (e, t) => {
	let n = ac(e), r = (e, r = t) => lc(n, e, r);
	return Object.assign(r, n), r;
}, dc = (e, t) => e ? uc(e, t) : uc;
//#endregion
//#region node_modules/zustand/esm/shallow.mjs
function Y(e, t) {
	if (Object.is(e, t)) return !0;
	if (typeof e != "object" || !e || typeof t != "object" || !t) return !1;
	if (e instanceof Map && t instanceof Map) {
		if (e.size !== t.size) return !1;
		for (let [n, r] of e) if (!Object.is(r, t.get(n))) return !1;
		return !0;
	}
	if (e instanceof Set && t instanceof Set) {
		if (e.size !== t.size) return !1;
		for (let n of e) if (!t.has(n)) return !1;
		return !0;
	}
	let n = Object.keys(e);
	if (n.length !== Object.keys(t).length) return !1;
	for (let r of n) if (!Object.prototype.hasOwnProperty.call(t, r) || !Object.is(e[r], t[r])) return !1;
	return !0;
}
m();
var fc = (0, b.createContext)(null), pc = fc.Provider, X = ha.error001("react");
function Z(e, t) {
	let n = (0, b.useContext)(fc);
	if (n === null) throw Error(X);
	return lc(n, e, t);
}
function Q() {
	let e = (0, b.useContext)(fc);
	if (e === null) throw Error(X);
	return (0, b.useMemo)(() => ({
		getState: e.getState,
		setState: e.setState,
		subscribe: e.subscribe
	}), [e]);
}
var mc = { display: "none" }, hc = {
	position: "absolute",
	width: 1,
	height: 1,
	margin: -1,
	border: 0,
	padding: 0,
	overflow: "hidden",
	clip: "rect(0px, 0px, 0px, 0px)",
	clipPath: "inset(100%)"
}, gc = "react-flow__node-desc", _c = "react-flow__edge-desc", vc = "react-flow__aria-live", yc = (e) => e.ariaLiveMessage, bc = (e) => e.ariaLabelConfig;
function xc({ rfId: e }) {
	let t = Z(yc);
	return (0, x.jsx)("div", {
		id: `${vc}-${e}`,
		"aria-live": "assertive",
		"aria-atomic": "true",
		style: hc,
		children: t
	});
}
function Sc({ rfId: e, disableKeyboardA11y: t }) {
	let n = Z(bc);
	return (0, x.jsxs)(x.Fragment, { children: [
		(0, x.jsx)("div", {
			id: `${gc}-${e}`,
			style: mc,
			children: t ? n["node.a11yDescription.default"] : n["node.a11yDescription.keyboardDisabled"]
		}),
		(0, x.jsx)("div", {
			id: `${_c}-${e}`,
			style: mc,
			children: n["edge.a11yDescription.default"]
		}),
		!t && (0, x.jsx)(xc, { rfId: e })
	] });
}
var Cc = (0, b.forwardRef)(({ position: e = "top-left", children: t, className: n, style: r, ...i }, a) => (0, x.jsx)("div", {
	className: S([
		"react-flow__panel",
		n,
		...`${e}`.split("-")
	]),
	style: r,
	ref: a,
	...i,
	children: t
}));
Cc.displayName = "Panel";
var wc = "https://reactflow.dev?utm_source=attribution";
function Tc({ proOptions: e, position: t = "bottom-right" }) {
	return e?.hideAttribution ? null : (0, x.jsx)(Cc, {
		position: t,
		className: "react-flow__attribution",
		"data-message": `Please only hide this attribution when you are subscribed to React Flow Pro: ${wc}`,
		children: (0, x.jsx)("a", {
			href: wc,
			target: "_blank",
			rel: "noopener noreferrer",
			"aria-label": "React Flow attribution",
			children: "React Flow"
		})
	});
}
var Ec = (e) => {
	let t = [], n = [];
	for (let [, n] of e.nodeLookup) n.selected && t.push(n.internals.userNode);
	for (let [, t] of e.edgeLookup) t.selected && n.push(t);
	return {
		selectedNodes: t,
		selectedEdges: n
	};
}, Dc = (e) => e.id;
function Oc(e, t) {
	return Y(e.selectedNodes.map(Dc), t.selectedNodes.map(Dc)) && Y(e.selectedEdges.map(Dc), t.selectedEdges.map(Dc));
}
function kc({ onSelectionChange: e }) {
	let t = Q(), { selectedNodes: n, selectedEdges: r } = Z(Ec, Oc);
	return (0, b.useEffect)(() => {
		let i = {
			nodes: n,
			edges: r
		};
		e?.(i), t.getState().onSelectionChangeHandlers.forEach((e) => e(i));
	}, [
		n,
		r,
		e
	]), null;
}
var Ac = (e) => !!e.onSelectionChangeHandlers;
function jc({ onSelectionChange: e }) {
	let t = Z(Ac);
	return e || t ? (0, x.jsx)(kc, { onSelectionChange: e }) : null;
}
var Mc = [0, 0], Nc = {
	x: 0,
	y: 0,
	zoom: 1
}, Pc = [.../* @__PURE__ */ "nodes.edges.defaultNodes.defaultEdges.onConnect.onConnectStart.onConnectEnd.onClickConnectStart.onClickConnectEnd.nodesDraggable.autoPanOnNodeFocus.nodesConnectable.nodesFocusable.edgesFocusable.edgesReconnectable.elevateNodesOnSelect.elevateEdgesOnSelect.minZoom.maxZoom.nodeExtent.onNodesChange.onEdgesChange.elementsSelectable.connectionMode.snapGrid.snapToGrid.translateExtent.connectOnClick.defaultEdgeOptions.fitView.fitViewOptions.onNodesDelete.onEdgesDelete.onDelete.onNodeDrag.onNodeDragStart.onNodeDragStop.onSelectionDrag.onSelectionDragStart.onSelectionDragStop.onMoveStart.onMove.onMoveEnd.noPanClassName.nodeOrigin.autoPanOnConnect.autoPanOnNodeDrag.onError.connectionRadius.isValidConnection.selectNodesOnDrag.nodeDragThreshold.connectionDragThreshold.onBeforeDelete.debug.autoPanSpeed.ariaLabelConfig.zIndexMode".split("."), "rfId"], Fc = (e) => ({
	setNodes: e.setNodes,
	setEdges: e.setEdges,
	setMinZoom: e.setMinZoom,
	setMaxZoom: e.setMaxZoom,
	setTranslateExtent: e.setTranslateExtent,
	setNodeExtent: e.setNodeExtent,
	reset: e.reset,
	setDefaultNodesAndEdges: e.setDefaultNodesAndEdges
}), Ic = {
	translateExtent: ga,
	nodeOrigin: Mc,
	minZoom: .5,
	maxZoom: 2,
	elementsSelectable: !0,
	noPanClassName: "nopan",
	rfId: "1"
};
function Lc(e) {
	let { setNodes: t, setEdges: n, setMinZoom: r, setMaxZoom: i, setTranslateExtent: a, setNodeExtent: o, reset: s, setDefaultNodesAndEdges: c } = Z(Fc, Y), l = Q();
	(0, b.useEffect)(() => (c(e.defaultNodes, e.defaultEdges), () => {
		u.current = Ic, s();
	}), []);
	let u = (0, b.useRef)(Ic);
	return (0, b.useEffect)(() => {
		for (let s of Pc) {
			let c = e[s];
			c !== u.current[s] && e[s] !== void 0 && (s === "nodes" ? t(c) : s === "edges" ? n(c) : s === "minZoom" ? r(c) : s === "maxZoom" ? i(c) : s === "translateExtent" ? a(c) : s === "nodeExtent" ? o(c) : s === "ariaLabelConfig" ? l.setState({ ariaLabelConfig: ho(c) }) : s === "fitView" ? l.setState({ fitViewQueued: c }) : s === "fitViewOptions" ? l.setState({ fitViewOptions: c }) : l.setState({ [s]: c }));
		}
		u.current = e;
	}, Pc.map((t) => e[t])), null;
}
function Rc() {
	return typeof window > "u" || !window.matchMedia ? null : window.matchMedia("(prefers-color-scheme: dark)");
}
function zc(e) {
	let [t, n] = (0, b.useState)(e === "system" ? null : e);
	return (0, b.useEffect)(() => {
		if (e !== "system") {
			n(e);
			return;
		}
		let t = Rc(), r = () => n(t?.matches ? "dark" : "light");
		return r(), t?.addEventListener("change", r), () => {
			t?.removeEventListener("change", r);
		};
	}, [e]), t === null ? Rc()?.matches ? "dark" : "light" : t;
}
var Bc = typeof document < "u" ? document : null;
function $(e = null, t = {
	target: Bc,
	actInsideInputWithModifier: !0
}) {
	let [n, r] = (0, b.useState)(!1), i = (0, b.useRef)(!1), a = (0, b.useRef)(/* @__PURE__ */ new Set([])), [o, s] = (0, b.useMemo)(() => {
		if (e !== null) {
			let t = (Array.isArray(e) ? e : [e]).filter((e) => typeof e == "string").map((e) => e.replace("+", "\n").replace("\n\n", "\n+").split("\n"));
			return [t, t.reduce((e, t) => e.concat(...t), [])];
		}
		return [[], []];
	}, [e]);
	return (0, b.useEffect)(() => {
		let n = t?.target ?? Bc, c = t?.actInsideInputWithModifier ?? !0;
		if (e !== null) {
			let e = (e) => {
				if (i.current = e.ctrlKey || e.metaKey || e.shiftKey || e.altKey, (!i.current || i.current && !c) && yo(e)) return !1;
				let n = Hc(e.code, s);
				if (a.current.add(e[n]), Vc(o, a.current, !1)) {
					let n = e.composedPath?.()?.[0] || e.target, a = n?.nodeName === "BUTTON" || n?.nodeName === "A";
					t.preventDefault !== !1 && (i.current || !a) && e.preventDefault(), r(!0);
				}
			}, l = (e) => {
				let t = Hc(e.code, s);
				Vc(o, a.current, !0) ? (r(!1), a.current.clear()) : a.current.delete(e[t]), e.key === "Meta" && a.current.clear(), i.current = !1;
			}, u = () => {
				a.current.clear(), r(!1);
			};
			return n?.addEventListener("keydown", e), n?.addEventListener("keyup", l), window.addEventListener("blur", u), window.addEventListener("contextmenu", u), () => {
				n?.removeEventListener("keydown", e), n?.removeEventListener("keyup", l), window.removeEventListener("blur", u), window.removeEventListener("contextmenu", u);
			};
		}
	}, [e, r]), n;
}
function Vc(e, t, n) {
	return e.filter((e) => n || e.length === t.size).some((e) => e.every((e) => t.has(e)));
}
function Hc(e, t) {
	return t.includes(e) ? "code" : "key";
}
var Uc = () => {
	let e = Q();
	return (0, b.useMemo)(() => ({
		zoomIn: async (t) => {
			let { panZoom: n } = e.getState();
			return n ? n.scaleBy(1.2, t) : !1;
		},
		zoomOut: async (t) => {
			let { panZoom: n } = e.getState();
			return n ? n.scaleBy(1 / 1.2, t) : !1;
		},
		zoomTo: async (t, n) => {
			let { panZoom: r } = e.getState();
			return r ? r.scaleTo(t, n) : !1;
		},
		getZoom: () => e.getState().transform[2],
		setViewport: async (t, n) => {
			let { transform: [r, i, a], panZoom: o } = e.getState();
			return o ? (await o.setViewport({
				x: t.x ?? r,
				y: t.y ?? i,
				zoom: t.zoom ?? a
			}, n), !0) : !1;
		},
		getViewport: () => {
			let [t, n, r] = e.getState().transform;
			return {
				x: t,
				y: n,
				zoom: r
			};
		},
		setCenter: async (t, n, r) => e.getState().setCenter(t, n, r),
		fitBounds: async (t, n) => {
			let { width: r, height: i, minZoom: a, maxZoom: o, panZoom: s } = e.getState(), c = oo(t, r, i, a, o, n?.padding ?? .1);
			return s ? (await s.setViewport(c, {
				duration: n?.duration,
				ease: n?.ease,
				interpolate: n?.interpolate
			}), !0) : !1;
		},
		screenToFlowPosition: (t, n = {}) => {
			let { transform: r, snapGrid: i, snapToGrid: a, domNode: o } = e.getState();
			if (!o) return t;
			let { x: s, y: c } = o.getBoundingClientRect(), l = {
				x: t.x - s,
				y: t.y - c
			}, u = n.snapGrid ?? i;
			return to(l, r, n.snapToGrid ?? a, u);
		},
		flowToScreenPosition: (t) => {
			let { transform: n, domNode: r } = e.getState();
			if (!r) return t;
			let { x: i, y: a } = r.getBoundingClientRect(), o = no(t, n);
			return {
				x: o.x + i,
				y: o.y + a
			};
		}
	}), []);
};
function Wc(e, t) {
	let n = [], r = /* @__PURE__ */ new Map(), i = [];
	for (let t of e) if (t.type === "add") {
		i.push(t);
		continue;
	} else if (t.type === "remove" || t.type === "replace") r.set(t.id, [t]);
	else {
		let e = r.get(t.id);
		e ? e.push(t) : r.set(t.id, [t]);
	}
	for (let e of t) {
		let t = r.get(e.id);
		if (!t) {
			n.push(e);
			continue;
		}
		if (t[0].type === "remove") continue;
		if (t[0].type === "replace") {
			n.push({ ...t[0].item });
			continue;
		}
		let i = { ...e };
		for (let e of t) Gc(e, i);
		n.push(i);
	}
	return i.length && i.forEach((e) => {
		e.index === void 0 ? n.push({ ...e.item }) : n.splice(e.index, 0, { ...e.item });
	}), n;
}
function Gc(e, t) {
	switch (e.type) {
		case "select":
			t.selected = e.selected;
			break;
		case "position":
			e.position !== void 0 && (t.position = e.position), e.dragging !== void 0 && (t.dragging = e.dragging);
			break;
		case "dimensions":
			e.dimensions !== void 0 && (t.measured = { ...e.dimensions }, e.setAttributes && ((e.setAttributes === !0 || e.setAttributes === "width") && (t.width = e.dimensions.width), (e.setAttributes === !0 || e.setAttributes === "height") && (t.height = e.dimensions.height))), typeof e.resizing == "boolean" && (t.resizing = e.resizing);
			break;
	}
}
function Kc(e, t) {
	return Wc(e, t);
}
function qc(e, t) {
	return Wc(e, t);
}
function Jc(e, t) {
	return {
		id: e,
		type: "select",
		selected: t
	};
}
function Yc(e, t = /* @__PURE__ */ new Set(), n = !1) {
	let r = [];
	for (let [i, a] of e) {
		let e = t.has(i);
		!(a.selected === void 0 && !e) && a.selected !== e && (n && (a.selected = e), r.push(Jc(a.id, e)));
	}
	return r;
}
function Xc({ items: e = [], lookup: t }) {
	let n = [], r = new Map(e.map((e) => [e.id, e]));
	for (let [r, i] of e.entries()) {
		let e = t.get(i.id), a = e?.internals?.userNode ?? e;
		a !== void 0 && a !== i && n.push({
			id: i.id,
			item: i,
			type: "replace"
		}), a === void 0 && n.push({
			item: i,
			type: "add",
			index: r
		});
	}
	for (let [e] of t) r.get(e) === void 0 && n.push({
		id: e,
		type: "remove"
	});
	return n;
}
function Zc(e) {
	return {
		id: e.id,
		type: "remove"
	};
}
var Qc = $a("React Flow", "https://reactflow.dev/");
function $c(e, t, n = {}) {
	return Mo(e, t, {
		...n,
		onError: n.onError ?? Qc
	});
}
var el = (e) => Da(e), tl = (e) => Ea(e);
function nl(e) {
	return (0, b.forwardRef)(e);
}
var rl = typeof window < "u" ? b.useLayoutEffect : b.useEffect;
function il(e) {
	let [t, n] = (0, b.useState)(BigInt(0)), [r] = (0, b.useState)(() => al(() => n((e) => e + BigInt(1))));
	return rl(() => {
		let t = r.get();
		t.length && (e(t), r.reset());
	}, [t]), r;
}
function al(e) {
	let t = [];
	return {
		get: () => t,
		reset: () => {
			t = [];
		},
		push: (n) => {
			t.push(n), e();
		}
	};
}
var ol = (0, b.createContext)(null);
function sl({ children: e }) {
	let t = Q(), n = il((0, b.useCallback)((e) => {
		let { nodes: n = [], setNodes: r, hasDefaultNodes: i, onNodesChange: a, nodeLookup: o, fitViewQueued: s, onNodesChangeMiddlewareMap: c } = t.getState(), l = n;
		for (let t of e) l = typeof t == "function" ? t(l) : t;
		let u = Xc({
			items: l,
			lookup: o
		});
		for (let e of c.values()) u = e(u);
		i && r(l), u.length > 0 ? a?.(u) : s && window.requestAnimationFrame(() => {
			let { fitViewQueued: e, nodes: n, setNodes: r } = t.getState();
			e && r(n);
		});
	}, [])), r = il((0, b.useCallback)((e) => {
		let { edges: n = [], setEdges: r, hasDefaultEdges: i, onEdgesChange: a, edgeLookup: o } = t.getState(), s = n;
		for (let t of e) s = typeof t == "function" ? t(s) : t;
		i ? r(s) : a && a(Xc({
			items: s,
			lookup: o
		}));
	}, [])), i = (0, b.useMemo)(() => ({
		nodeQueue: n,
		edgeQueue: r
	}), []);
	return (0, x.jsx)(ol.Provider, {
		value: i,
		children: e
	});
}
function cl() {
	let e = (0, b.useContext)(ol);
	if (!e) throw Error("useBatchContext must be used within a BatchProvider");
	return e;
}
var ll = (e) => !!e.panZoom;
function ul() {
	let e = Uc(), t = Q(), n = cl(), r = Z(ll), i = (0, b.useMemo)(() => {
		let e = (e) => t.getState().nodeLookup.get(e), r = (e) => {
			n.nodeQueue.push(e);
		}, i = (e) => {
			n.edgeQueue.push(e);
		}, a = (e) => {
			let { nodeLookup: n, nodeOrigin: r } = t.getState(), i = el(e) ? e : n.get(e.id), a = i.parentId ? fo(i.position, i.measured, i.parentId, n, r) : i.position;
			return Ka({
				...i,
				position: a,
				width: i.measured?.width ?? i.width,
				height: i.measured?.height ?? i.height
			});
		}, o = (e, t, n = { replace: !1 }) => {
			r((r) => r.map((r) => {
				if (r.id === e) {
					let e = typeof t == "function" ? t(r) : t;
					return n.replace && el(e) ? e : {
						...r,
						...e
					};
				}
				return r;
			}));
		}, s = (e, t, n = { replace: !1 }) => {
			i((r) => r.map((r) => {
				if (r.id === e) {
					let e = typeof t == "function" ? t(r) : t;
					return n.replace && tl(e) ? e : {
						...r,
						...e
					};
				}
				return r;
			}));
		};
		return {
			getNodes: () => t.getState().nodes.map((e) => ({ ...e })),
			getNode: (t) => e(t)?.internals.userNode,
			getInternalNode: e,
			getEdges: () => {
				let { edges: e = [] } = t.getState();
				return e.map((e) => ({ ...e }));
			},
			getEdge: (e) => t.getState().edgeLookup.get(e),
			setNodes: r,
			setEdges: i,
			addNodes: (e) => {
				let t = Array.isArray(e) ? e : [e];
				n.nodeQueue.push((e) => [...e, ...t]);
			},
			addEdges: (e) => {
				let t = Array.isArray(e) ? e : [e];
				n.edgeQueue.push((e) => [...e, ...t]);
			},
			toObject: () => {
				let { nodes: e = [], edges: n = [], transform: r } = t.getState(), [i, a, o] = r;
				return {
					nodes: e.map((e) => ({ ...e })),
					edges: n.map((e) => ({ ...e })),
					viewport: {
						x: i,
						y: a,
						zoom: o
					}
				};
			},
			deleteElements: async ({ nodes: e = [], edges: n = [] }) => {
				let { nodes: r, edges: i, onNodesDelete: a, onEdgesDelete: o, triggerNodeChanges: s, triggerEdgeChanges: c, onDelete: l, onBeforeDelete: u } = t.getState(), { nodes: d, edges: f } = await La({
					nodesToRemove: e,
					edgesToRemove: n,
					nodes: r,
					edges: i,
					onBeforeDelete: u
				}), p = f.length > 0, m = d.length > 0;
				if (p) {
					let e = f.map(Zc);
					o?.(f), c(e);
				}
				if (m) {
					let e = d.map(Zc);
					a?.(d), s(e);
				}
				return (m || p) && l?.({
					nodes: d,
					edges: f
				}), {
					deletedNodes: d,
					deletedEdges: f
				};
			},
			getIntersectingNodes: (e, n = !0, r) => {
				let i = Za(e), o = i ? e : a(e), s = r !== void 0;
				return o ? (r || t.getState().nodes).filter((r) => {
					let a = t.getState().nodeLookup.get(r.id);
					if (a && !i && (r.id === e.id || !a.internals.positionAbsolute)) return !1;
					let c = Ka(s ? r : a), l = Xa(c, o);
					return n && l > 0 || l >= c.width * c.height || l >= o.width * o.height;
				}) : [];
			},
			isNodeIntersecting: (e, t, n = !0) => {
				let r = Za(e) ? e : a(e);
				if (!r) return !1;
				let i = Xa(r, t);
				return n && i > 0 || i >= t.width * t.height || i >= r.width * r.height;
			},
			updateNode: o,
			updateNodeData: (e, t, n = { replace: !1 }) => {
				o(e, (e) => {
					let r = typeof t == "function" ? t(e) : t;
					return n.replace ? {
						...e,
						data: r
					} : {
						...e,
						data: {
							...e.data,
							...r
						}
					};
				}, n);
			},
			updateEdge: s,
			updateEdgeData: (e, t, n = { replace: !1 }) => {
				s(e, (e) => {
					let r = typeof t == "function" ? t(e) : t;
					return n.replace ? {
						...e,
						data: r
					} : {
						...e,
						data: {
							...e.data,
							...r
						}
					};
				}, n);
			},
			getNodesBounds: (e) => {
				let { nodeLookup: n, nodeOrigin: r } = t.getState();
				return Aa(e, {
					nodeLookup: n,
					nodeOrigin: r
				});
			},
			getHandleConnections: ({ type: e, id: n, nodeId: r }) => Array.from(t.getState().connectionLookup.get(`${r}-${e}${n ? `-${n}` : ""}`)?.values() ?? []),
			getNodeConnections: ({ type: e, handleId: n, nodeId: r }) => Array.from(t.getState().connectionLookup.get(`${r}${e ? n ? `-${e}-${n}` : `-${e}` : ""}`)?.values() ?? []),
			fitView: async (e) => {
				let r = t.getState().fitViewResolver ?? mo();
				return t.setState({
					fitViewQueued: !0,
					fitViewOptions: e,
					fitViewResolver: r
				}), n.nodeQueue.push((e) => [...e]), r.promise;
			}
		};
	}, []);
	return (0, b.useMemo)(() => ({
		...i,
		...e,
		viewportInitialized: r
	}), [r]);
}
var dl = (e) => e.selected, fl = typeof window < "u" ? window : void 0;
function pl({ deleteKeyCode: e, multiSelectionKeyCode: t }) {
	let n = Q(), { deleteElements: r } = ul(), i = $(e, { actInsideInputWithModifier: !1 }), a = $(t, { target: fl });
	(0, b.useEffect)(() => {
		if (i) {
			let { edges: e, nodes: t } = n.getState();
			r({
				nodes: t.filter(dl),
				edges: e.filter(dl)
			}), n.setState({ nodesSelectionActive: !1 });
		}
	}, [i]), (0, b.useEffect)(() => {
		n.setState({ multiSelectionActive: a });
	}, [a]);
}
function ml(e) {
	let t = Q();
	(0, b.useEffect)(() => {
		let n = () => {
			if (!e.current || !(e.current.checkVisibility?.() ?? !0)) return !1;
			let n = J(e.current);
			(n.height === 0 || n.width === 0) && t.getState().onError?.("004", ha.error004()), t.setState({
				width: n.width || 500,
				height: n.height || 500
			});
		};
		if (e.current) {
			n(), window.addEventListener("resize", n);
			let t = new ResizeObserver(() => n());
			return t.observe(e.current), () => {
				window.removeEventListener("resize", n), t && e.current && t.unobserve(e.current);
			};
		}
	}, []);
}
var hl = {
	position: "absolute",
	width: "100%",
	height: "100%",
	top: 0,
	left: 0
}, gl = (e) => ({
	userSelectionActive: e.userSelectionActive,
	lib: e.lib,
	connectionInProgress: e.connection.inProgress
});
function _l({ onPaneContextMenu: e, zoomOnScroll: t = !0, zoomOnPinch: n = !0, panOnScroll: r = !1, panOnScrollSpeed: i = .5, panOnScrollMode: a = ba.Free, zoomOnDoubleClick: o = !0, panOnDrag: s = !0, defaultViewport: c, translateExtent: l, minZoom: u, maxZoom: d, zoomActivationKeyCode: f, preventScrolling: p = !0, children: m, noWheelClassName: h, noPanClassName: g, onViewportChange: _, isControlledViewport: v, paneClickDistance: y, selectionOnDrag: S }) {
	let C = Q(), w = (0, b.useRef)(null), { userSelectionActive: T, lib: E, connectionInProgress: D } = Z(gl, Y), O = $(f), k = (0, b.useRef)();
	ml(w);
	let A = (0, b.useCallback)((e) => {
		_?.({
			x: e[0],
			y: e[1],
			zoom: e[2]
		}), v || C.setState({ transform: e });
	}, [_, v]);
	return (0, b.useEffect)(() => {
		if (w.current) {
			k.current = Vs({
				domNode: w.current,
				minZoom: u,
				maxZoom: d,
				translateExtent: l,
				viewport: c,
				onDraggingChange: (e) => C.setState((t) => t.paneDragging === e ? t : { paneDragging: e }),
				onPanZoomStart: (e, t) => {
					let { onViewportChangeStart: n, onMoveStart: r } = C.getState();
					r?.(e, t), n?.(t);
				},
				onPanZoom: (e, t) => {
					let { onViewportChange: n, onMove: r } = C.getState();
					r?.(e, t), n?.(t);
				},
				onPanZoomEnd: (e, t) => {
					let { onViewportChangeEnd: n, onMoveEnd: r } = C.getState();
					r?.(e, t), n?.(t);
				}
			});
			let { x: e, y: t, zoom: n } = k.current.getViewport();
			return C.setState({
				panZoom: k.current,
				transform: [
					e,
					t,
					n
				],
				domNode: w.current.closest(".react-flow")
			}), () => {
				k.current?.destroy();
			};
		}
	}, []), (0, b.useEffect)(() => {
		k.current?.update({
			onPaneContextMenu: e,
			zoomOnScroll: t,
			zoomOnPinch: n,
			panOnScroll: r,
			panOnScrollSpeed: i,
			panOnScrollMode: a,
			zoomOnDoubleClick: o,
			panOnDrag: s,
			zoomActivationKeyPressed: O,
			preventScrolling: p,
			noPanClassName: g,
			userSelectionActive: T,
			noWheelClassName: h,
			lib: E,
			onTransformChange: A,
			connectionInProgress: D,
			selectionOnDrag: S,
			paneClickDistance: y
		});
	}, [
		e,
		t,
		n,
		r,
		i,
		a,
		o,
		s,
		O,
		p,
		g,
		T,
		h,
		E,
		A,
		D,
		S,
		y
	]), (0, x.jsx)("div", {
		className: "react-flow__renderer",
		ref: w,
		style: hl,
		children: m
	});
}
var vl = (e) => ({
	userSelectionActive: e.userSelectionActive,
	userSelectionRect: e.userSelectionRect
});
function yl() {
	let { userSelectionActive: e, userSelectionRect: t } = Z(vl, Y);
	return e && t ? (0, x.jsx)("div", {
		className: "react-flow__selection react-flow__container",
		style: {
			width: t.width,
			height: t.height,
			transform: `translate(${t.x}px, ${t.y}px)`
		}
	}) : null;
}
var bl = (e, t) => (n) => {
	n.target === t.current && e?.(n);
}, xl = (e) => ({
	userSelectionActive: e.userSelectionActive,
	elementsSelectable: e.elementsSelectable,
	dragging: e.paneDragging,
	panBy: e.panBy,
	autoPanSpeed: e.autoPanSpeed
});
function Sl({ isSelecting: e, selectionKeyPressed: t, selectionMode: n = xa.Full, panOnDrag: r, autoPanOnSelection: i, paneClickDistance: a, selectionOnDrag: o, onSelectionStart: s, onSelectionEnd: c, onPaneClick: l, onPaneContextMenu: u, onPaneScroll: d, onPaneMouseEnter: f, onPaneMouseMove: p, onPaneMouseLeave: m, children: h }) {
	let g = (0, b.useRef)(0), _ = Q(), { userSelectionActive: v, elementsSelectable: y, dragging: C, panBy: w, autoPanSpeed: T } = Z(xl, Y), E = y && (e || v), D = (0, b.useRef)(null), O = (0, b.useRef)(), k = (0, b.useRef)(/* @__PURE__ */ new Set()), A = (0, b.useRef)(/* @__PURE__ */ new Set()), j = (0, b.useRef)(!1), M = (0, b.useRef)(!1), N = (0, b.useRef)({
		x: 0,
		y: 0
	}), P = (0, b.useRef)(!1), F = (e) => {
		if (M.current || j.current || _.getState().connection.inProgress) {
			M.current = !1, j.current = !1;
			return;
		}
		l?.(e), _.getState().resetSelectedElements(), _.setState({ nodesSelectionActive: !1 });
	}, I = (e) => {
		if (Array.isArray(r) && r?.includes(2)) {
			e.preventDefault();
			return;
		}
		u?.(e);
	}, ee = d ? (e) => d(e) : void 0, L = (e) => {
		M.current &&= (e.stopPropagation(), !1);
	}, R = (n) => {
		let { domNode: r, transform: i } = _.getState();
		if (O.current = r?.getBoundingClientRect(), !O.current) return;
		let a = n.target === D.current;
		if (!a && n.target.closest(".nokey") || !e || !(o && a || t) || n.button !== 0 || !n.isPrimary) return;
		n.target?.setPointerCapture?.(n.pointerId), M.current = !1;
		let { x: s, y: c } = xo(n.nativeEvent, O.current), l = to({
			x: s,
			y: c
		}, i);
		_.setState({ userSelectionRect: {
			width: 0,
			height: 0,
			startX: l.x,
			startY: l.y,
			x: s,
			y: c
		} }), a || (n.stopPropagation(), n.preventDefault());
	};
	function z(e, t) {
		let { userSelectionRect: r } = _.getState();
		if (!r) return;
		let { transform: i, nodeLookup: a, edgeLookup: o, connectionLookup: s, triggerNodeChanges: c, triggerEdgeChanges: l, defaultEdgeOptions: u } = _.getState(), d = {
			x: r.startX,
			y: r.startY
		}, { x: f, y: p } = no(d, i), m = {
			startX: d.x,
			startY: d.y,
			x: e < f ? e : f,
			y: t < p ? t : p,
			width: Math.abs(e - f),
			height: Math.abs(t - p)
		}, h = k.current, g = A.current;
		k.current = new Set(Ma(a, m, i, n === xa.Partial, !0).map((e) => e.id)), A.current = /* @__PURE__ */ new Set();
		let v = u?.selectable ?? !0;
		for (let e of k.current) {
			let t = s.get(e);
			if (t) for (let { edgeId: e } of t.values()) {
				let t = o.get(e);
				t && (t.selectable ?? v) && A.current.add(e);
			}
		}
		po(h, k.current) || c(Yc(a, k.current, !0)), po(g, A.current) || l(Yc(o, A.current)), _.setState({
			userSelectionRect: m,
			userSelectionActive: !0,
			nodesSelectionActive: !1
		});
	}
	function B() {
		if (!i || !O.current) return;
		let [e, t] = Ha(N.current, O.current, T);
		w({
			x: e,
			y: t
		}).then((e) => {
			if (!M.current || !e) {
				g.current = requestAnimationFrame(B);
				return;
			}
			let { x: t, y: n } = N.current;
			z(t, n), g.current = requestAnimationFrame(B);
		});
	}
	let te = () => {
		cancelAnimationFrame(g.current), g.current = 0, P.current = !1;
	};
	return (0, b.useEffect)(() => () => te(), []), (0, x.jsxs)("div", {
		className: S(["react-flow__pane", {
			draggable: r === !0 || Array.isArray(r) && r.includes(0),
			dragging: C,
			selection: e
		}]),
		onClick: E ? void 0 : bl(F, D),
		onContextMenu: bl(I, D),
		onWheel: bl(ee, D),
		onPointerEnter: E ? void 0 : f,
		onPointerMove: E ? (e) => {
			let { userSelectionRect: n, transform: r, resetSelectedElements: i } = _.getState();
			if (!O.current || !n) return;
			let { x: o, y: c } = xo(e.nativeEvent, O.current);
			N.current = {
				x: o,
				y: c
			};
			let l = no({
				x: n.startX,
				y: n.startY
			}, r);
			if (!M.current) {
				let n = t ? 0 : a;
				if (Math.hypot(o - l.x, c - l.y) <= n) return;
				i(), s?.(e);
			}
			M.current = !0, P.current ||= (B(), !0), z(o, c);
		} : p,
		onPointerUp: (e) => {
			if (!E) {
				e.target === D.current && _.getState().connection.inProgress && (j.current = !0);
				return;
			}
			e.button === 0 && (e.target?.releasePointerCapture?.(e.pointerId), !v && e.target === D.current && _.getState().userSelectionRect && F?.(e), _.setState({
				userSelectionActive: !1,
				userSelectionRect: null
			}), M.current && (c?.(e), _.setState({ nodesSelectionActive: k.current.size > 0 })), te());
		},
		onPointerCancel: E ? (e) => {
			e.target?.releasePointerCapture?.(e.pointerId), te();
		} : void 0,
		onPointerDownCapture: E ? R : void 0,
		onClickCapture: E ? L : void 0,
		onPointerLeave: m,
		ref: D,
		style: hl,
		children: [h, (0, x.jsx)(yl, {})]
	});
}
function Cl({ id: e, store: t, unselect: n = !1, nodeRef: r }) {
	let { addSelectedNodes: i, unselectNodesAndEdges: a, multiSelectionActive: o, nodeLookup: s, onError: c } = t.getState(), l = s.get(e);
	if (!l) {
		c?.("012", ha.error012(e));
		return;
	}
	t.setState({ nodesSelectionActive: !1 }), l.selected ? (n || l.selected && o) && (a({
		nodes: [l],
		edges: []
	}), requestAnimationFrame(() => r?.current?.blur())) : i([e]);
}
function wl({ nodeRef: e, disabled: t = !1, noDragClassName: n, handleSelector: r, nodeId: i, isSelectable: a, nodeClickDistance: o }) {
	let s = Q(), [c, l] = (0, b.useState)(!1), u = (0, b.useRef)();
	return (0, b.useEffect)(() => {
		u.current = gs({
			getStoreItems: () => s.getState(),
			onNodeMouseDown: (t) => {
				Cl({
					id: t,
					store: s,
					nodeRef: e
				});
			},
			onDragStart: () => {
				l(!0);
			},
			onDragStop: () => {
				l(!1);
			}
		});
	}, []), (0, b.useEffect)(() => {
		if (!(t || !e.current || !u.current)) return u.current.update({
			noDragClassName: n,
			handleSelector: r,
			domNode: e.current,
			isSelectable: a,
			nodeId: i,
			nodeClickDistance: o
		}), () => {
			u.current?.destroy();
		};
	}, [
		n,
		r,
		t,
		a,
		e,
		i,
		o
	]), c;
}
var Tl = (e) => (t) => t.selected && (t.draggable || e && t.draggable === void 0);
function El() {
	let e = Q();
	return (0, b.useCallback)((t) => {
		let { nodeExtent: n, snapToGrid: r, snapGrid: i, nodesDraggable: a, onError: o, updateNodePositions: s, nodeLookup: c, nodeOrigin: l } = e.getState(), u = /* @__PURE__ */ new Map(), d = Tl(a), f = r ? i[0] : 5, p = r ? i[1] : 5, m = t.direction.x * f * t.factor, h = t.direction.y * p * t.factor;
		for (let [, e] of c) {
			if (!d(e)) continue;
			let t = {
				x: e.internals.positionAbsolute.x + m,
				y: e.internals.positionAbsolute.y + h
			};
			r && (t = eo(t, i));
			let { position: a, positionAbsolute: s } = Ia({
				nodeId: e.id,
				nextPosition: t,
				nodeLookup: c,
				nodeExtent: n,
				nodeOrigin: l,
				onError: o
			});
			e.position = a, e.internals.positionAbsolute = s, u.set(e.id, e);
		}
		s(u);
	}, []);
}
var Dl = (0, b.createContext)(null), Ol = Dl.Provider;
Dl.Consumer;
var kl = () => (0, b.useContext)(Dl), Al = (e) => ({
	connectOnClick: e.connectOnClick,
	noPanClassName: e.noPanClassName,
	rfId: e.rfId
}), jl = (0, b.createContext)(null);
function Ml({ children: e }) {
	let t = Z(Al, Y);
	return (0, x.jsx)(jl.Provider, {
		value: t,
		children: e
	});
}
function Nl() {
	let e = (0, b.useContext)(jl);
	if (!e) throw Error("useHandleConfig must be used within a HandleConfigProvider");
	return e;
}
var Pl = {
	connectingFrom: !1,
	connectingTo: !1,
	clickConnecting: !1,
	isPossibleEndHandle: !0,
	connectionInProcess: !1,
	clickConnectionInProcess: !1,
	valid: !1
}, Fl = (e, t, n) => (r) => {
	let { connectionClickStartHandle: i, connectionMode: a, connection: o } = r, { fromHandle: s, toHandle: c, isValid: l } = o;
	if (!s && !i) return Pl;
	let u = c?.nodeId === e && c?.id === t && c?.type === n;
	return {
		connectingFrom: s?.nodeId === e && s?.id === t && s?.type === n,
		connectingTo: u,
		clickConnecting: i?.nodeId === e && i?.id === t && i?.type === n,
		isPossibleEndHandle: a === ya.Strict ? s?.type !== n : e !== s?.nodeId || t !== s?.id,
		connectionInProcess: !!s,
		clickConnectionInProcess: !!i,
		valid: u && l
	};
};
function Il({ type: e = "source", position: t = q.Top, isValidConnection: n, isConnectable: r = !0, isConnectableStart: i = !0, isConnectableEnd: a = !0, id: o, onConnect: s, children: c, className: l, onMouseDown: u, onTouchStart: d, ...f }, p) {
	let m = o || null, h = e === "target", g = Q(), _ = kl(), { connectOnClick: v, noPanClassName: y, rfId: b } = Nl(), { connectingFrom: C, connectingTo: w, clickConnecting: T, isPossibleEndHandle: E, connectionInProcess: D, clickConnectionInProcess: O, valid: k } = Z(Fl(_, m, e), Y);
	_ || g.getState().onError?.("010", ha.error010());
	let A = (e) => {
		let { defaultEdgeOptions: t, onConnect: n, hasDefaultEdges: r } = g.getState(), i = {
			...t,
			...e
		};
		if (r) {
			let { edges: e, setEdges: t, onError: n } = g.getState();
			t($c(i, e, { onError: n }));
		}
		n?.(i), s?.(i);
	}, j = (e) => {
		if (!_) return;
		let t = bo(e.nativeEvent);
		if (i && (t && e.button === 0 || !t)) {
			let t = g.getState();
			Es.onPointerDown(e.nativeEvent, {
				handleDomNode: e.currentTarget,
				autoPanOnConnect: t.autoPanOnConnect,
				connectionMode: t.connectionMode,
				connectionRadius: t.connectionRadius,
				domNode: t.domNode,
				nodeLookup: t.nodeLookup,
				lib: t.lib,
				isTarget: h,
				handleId: m,
				nodeId: _,
				flowId: t.rfId,
				panBy: t.panBy,
				cancelConnection: t.cancelConnection,
				onConnectStart: t.onConnectStart,
				onConnectEnd: (...e) => g.getState().onConnectEnd?.(...e),
				updateConnection: t.updateConnection,
				onConnect: A,
				isValidConnection: n || ((...e) => g.getState().isValidConnection?.(...e) ?? !0),
				getTransform: () => g.getState().transform,
				getFromHandle: () => g.getState().connection.fromHandle,
				autoPanSpeed: t.autoPanSpeed,
				dragThreshold: t.connectionDragThreshold
			});
		}
		t ? u?.(e) : d?.(e);
	};
	return (0, x.jsx)("div", {
		"data-handleid": m,
		"data-nodeid": _,
		"data-handlepos": t,
		"data-id": `${b}-${_}-${m}-${e}`,
		className: S([
			"react-flow__handle",
			`react-flow__handle-${t}`,
			"nodrag",
			y,
			l,
			{
				source: !h,
				target: h,
				connectable: r,
				connectablestart: i,
				connectableend: a,
				clickconnecting: T,
				connectingfrom: C,
				connectingto: w,
				valid: k,
				connectionindicator: r && (!D || E) && (D || O ? a : i)
			}
		]),
		onMouseDown: j,
		onTouchStart: j,
		onClick: v ? (t) => {
			let { onClickConnectStart: r, onClickConnectEnd: a, connectionClickStartHandle: o, connectionMode: s, isValidConnection: c, lib: l, rfId: u, nodeLookup: d, connection: f } = g.getState();
			if (!_ || !o && !i) return;
			if (!o) {
				r?.(t.nativeEvent, {
					nodeId: _,
					handleId: m,
					handleType: e
				}), g.setState({ connectionClickStartHandle: {
					nodeId: _,
					type: e,
					id: m
				} });
				return;
			}
			let p = _o(t.target), h = n || c, { connection: v, isValid: y } = Es.isValid(t.nativeEvent, {
				handle: {
					nodeId: _,
					id: m,
					type: e
				},
				connectionMode: s,
				fromNodeId: o.nodeId,
				fromHandleId: o.id || null,
				fromType: o.type,
				isValidConnection: h,
				flowId: u,
				doc: p,
				lib: l,
				nodeLookup: d
			});
			y && v && A(v);
			let b = structuredClone(f);
			delete b.inProgress, b.toPosition = b.toHandle ? b.toHandle.position : null, a?.(t, b), g.setState({ connectionClickStartHandle: null });
		} : void 0,
		ref: p,
		...f,
		children: c
	});
}
var Ll = (0, b.memo)(nl(Il));
function Rl({ data: e, isConnectable: t, sourcePosition: n = q.Bottom }) {
	return (0, x.jsxs)(x.Fragment, { children: [e?.label, (0, x.jsx)(Ll, {
		type: "source",
		position: n,
		isConnectable: t
	})] });
}
function zl({ data: e, isConnectable: t, targetPosition: n = q.Top, sourcePosition: r = q.Bottom }) {
	return (0, x.jsxs)(x.Fragment, { children: [
		(0, x.jsx)(Ll, {
			type: "target",
			position: n,
			isConnectable: t
		}),
		e?.label,
		(0, x.jsx)(Ll, {
			type: "source",
			position: r,
			isConnectable: t
		})
	] });
}
function Bl() {
	return null;
}
function Vl({ data: e, isConnectable: t, targetPosition: n = q.Top }) {
	return (0, x.jsxs)(x.Fragment, { children: [(0, x.jsx)(Ll, {
		type: "target",
		position: n,
		isConnectable: t
	}), e?.label] });
}
var Hl = {
	ArrowUp: {
		x: 0,
		y: -1
	},
	ArrowDown: {
		x: 0,
		y: 1
	},
	ArrowLeft: {
		x: -1,
		y: 0
	},
	ArrowRight: {
		x: 1,
		y: 0
	}
}, Ul = {
	input: Rl,
	default: zl,
	output: Vl,
	group: Bl
};
function Wl(e) {
	return e.internals.handleBounds === void 0 ? {
		width: e.width ?? e.initialWidth ?? e.style?.width,
		height: e.height ?? e.initialHeight ?? e.style?.height
	} : {
		width: e.width ?? e.style?.width,
		height: e.height ?? e.style?.height
	};
}
var Gl = (e) => {
	let { width: t, height: n, x: r, y: i } = ja(e.nodeLookup, { filter: (e) => !!e.selected });
	return {
		width: Qa(t) ? t : null,
		height: Qa(n) ? n : null,
		userSelectionActive: e.userSelectionActive,
		transformString: `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]}) translate(${r}px,${i}px)`
	};
};
function Kl({ onSelectionContextMenu: e, noPanClassName: t, disableKeyboardA11y: n }) {
	let r = Q(), { width: i, height: a, transformString: o, userSelectionActive: s } = Z(Gl, Y), c = El(), l = (0, b.useRef)(null);
	(0, b.useEffect)(() => {
		n || l.current?.focus({ preventScroll: !0 });
	}, [n]);
	let u = !s && i !== null && a !== null;
	if (wl({
		nodeRef: l,
		disabled: !u
	}), !u) return null;
	let d = e ? (t) => {
		e(t, r.getState().nodes.filter((e) => e.selected));
	} : void 0;
	return (0, x.jsx)("div", {
		className: S([
			"react-flow__nodesselection",
			"react-flow__container",
			t
		]),
		style: { transform: o },
		children: (0, x.jsx)("div", {
			ref: l,
			className: "react-flow__nodesselection-rect",
			onContextMenu: d,
			tabIndex: n ? void 0 : -1,
			onKeyDown: n ? void 0 : (e) => {
				Object.prototype.hasOwnProperty.call(Hl, e.key) && (e.preventDefault(), c({
					direction: Hl[e.key],
					factor: e.shiftKey ? 4 : 1
				}));
			},
			style: {
				width: i,
				height: a
			}
		})
	});
}
var ql = typeof window < "u" ? window : void 0, Jl = (e) => ({
	nodesSelectionActive: e.nodesSelectionActive,
	userSelectionActive: e.userSelectionActive
});
function Yl({ children: e, onPaneClick: t, onPaneMouseEnter: n, onPaneMouseMove: r, onPaneMouseLeave: i, onPaneContextMenu: a, onPaneScroll: o, paneClickDistance: s, deleteKeyCode: c, selectionKeyCode: l, selectionOnDrag: u, selectionMode: d, onSelectionStart: f, onSelectionEnd: p, multiSelectionKeyCode: m, panActivationKeyCode: h, zoomActivationKeyCode: g, elementsSelectable: _, zoomOnScroll: v, zoomOnPinch: y, panOnScroll: b, panOnScrollSpeed: S, panOnScrollMode: C, zoomOnDoubleClick: w, panOnDrag: T, autoPanOnSelection: E, defaultViewport: D, translateExtent: O, minZoom: k, maxZoom: A, preventScrolling: j, onSelectionContextMenu: M, noWheelClassName: N, noPanClassName: P, disableKeyboardA11y: F, onViewportChange: I, isControlledViewport: ee }) {
	let { nodesSelectionActive: L, userSelectionActive: R } = Z(Jl, Y), z = $(l, { target: ql }), B = $(h, { target: ql }), te = B || T, ne = B || b, re = u && te !== !0, ie = z || R || re;
	return pl({
		deleteKeyCode: c,
		multiSelectionKeyCode: m
	}), (0, x.jsx)(_l, {
		onPaneContextMenu: a,
		elementsSelectable: _,
		zoomOnScroll: v,
		zoomOnPinch: y,
		panOnScroll: ne,
		panOnScrollSpeed: S,
		panOnScrollMode: C,
		zoomOnDoubleClick: w,
		panOnDrag: !z && te,
		defaultViewport: D,
		translateExtent: O,
		minZoom: k,
		maxZoom: A,
		zoomActivationKeyCode: g,
		preventScrolling: j,
		noWheelClassName: N,
		noPanClassName: P,
		onViewportChange: I,
		isControlledViewport: ee,
		paneClickDistance: s,
		selectionOnDrag: re,
		children: (0, x.jsxs)(Sl, {
			onSelectionStart: f,
			onSelectionEnd: p,
			onPaneClick: t,
			onPaneMouseEnter: n,
			onPaneMouseMove: r,
			onPaneMouseLeave: i,
			onPaneContextMenu: a,
			onPaneScroll: o,
			panOnDrag: te,
			autoPanOnSelection: E,
			isSelecting: !!ie,
			selectionMode: d,
			selectionKeyPressed: z,
			paneClickDistance: s,
			selectionOnDrag: re,
			children: [e, L && (0, x.jsx)(Kl, {
				onSelectionContextMenu: M,
				noPanClassName: P,
				disableKeyboardA11y: F
			})]
		})
	});
}
Yl.displayName = "FlowRenderer";
var Xl = (0, b.memo)(Yl), Zl = (e) => (t) => e ? Ma(t.nodeLookup, {
	x: 0,
	y: 0,
	width: t.width,
	height: t.height
}, t.transform, !0).map((e) => e.id) : Array.from(t.nodeLookup.keys());
function Ql(e) {
	return Z((0, b.useCallback)(Zl(e), [e]), Y);
}
var $l = (e) => e.updateNodeInternals;
function eu() {
	let e = Z($l), [t] = (0, b.useState)(() => typeof ResizeObserver > "u" ? null : new ResizeObserver((t) => {
		let n = /* @__PURE__ */ new Map();
		t.forEach((e) => {
			let t = e.target.getAttribute("data-id");
			n.set(t, {
				id: t,
				nodeElement: e.target,
				force: !0
			});
		}), e(n);
	}));
	return (0, b.useEffect)(() => () => {
		t?.disconnect();
	}, [t]), t;
}
function tu({ node: e, nodeType: t, hasDimensions: n, resizeObserver: r }) {
	let i = Q(), a = (0, b.useRef)(null), o = (0, b.useRef)(null), s = (0, b.useRef)(e.sourcePosition), c = (0, b.useRef)(e.targetPosition), l = (0, b.useRef)(t), u = n && !!e.internals.handleBounds;
	return (0, b.useEffect)(() => {
		a.current && !e.hidden && (!u || o.current !== a.current) && (o.current && r?.unobserve(o.current), r?.observe(a.current), o.current = a.current);
	}, [u, e.hidden]), (0, b.useEffect)(() => () => {
		o.current &&= (r?.unobserve(o.current), null);
	}, []), (0, b.useEffect)(() => {
		if (a.current) {
			let n = l.current !== t, r = s.current !== e.sourcePosition, o = c.current !== e.targetPosition;
			(n || r || o) && (l.current = t, s.current = e.sourcePosition, c.current = e.targetPosition, i.getState().updateNodeInternals(/* @__PURE__ */ new Map([[e.id, {
				id: e.id,
				nodeElement: a.current,
				force: !0
			}]])));
		}
	}, [
		e.id,
		t,
		e.sourcePosition,
		e.targetPosition
	]), a;
}
function nu({ id: e, onClick: t, onMouseEnter: n, onMouseMove: r, onMouseLeave: i, onContextMenu: a, onDoubleClick: o, nodesDraggable: s, elementsSelectable: c, nodesConnectable: l, nodesFocusable: u, resizeObserver: d, noDragClassName: f, noPanClassName: p, disableKeyboardA11y: m, rfId: h, nodeTypes: g, nodeClickDistance: _, onError: v }) {
	let { node: y, internals: b, isParent: C } = Z((t) => {
		let n = t.nodeLookup.get(e), r = t.parentLookup.has(e);
		return {
			node: n,
			internals: n.internals,
			isParent: r
		};
	}, Y), w = y.type || "default", T = g?.[w] || Ul[w];
	T === void 0 && (v?.("003", ha.error003(w)), w = "default", T = g?.default || Ul.default);
	let E = !!(y.draggable || s && y.draggable === void 0), D = !!(y.selectable || c && y.selectable === void 0), O = !!(y.connectable || l && y.connectable === void 0), k = !!(y.focusable || u && y.focusable === void 0), A = Q(), j = uo(y), M = tu({
		node: y,
		nodeType: w,
		hasDimensions: j,
		resizeObserver: d
	}), N = wl({
		nodeRef: M,
		disabled: y.hidden || !E,
		noDragClassName: f,
		handleSelector: y.dragHandle,
		nodeId: e,
		isSelectable: D,
		nodeClickDistance: _
	}), P = El();
	if (y.hidden) return null;
	let F = lo(y), I = Wl(y), ee = D || E || t || n || r || i, L = n ? (e) => n(e, { ...b.userNode }) : void 0, R = r ? (e) => r(e, { ...b.userNode }) : void 0, z = i ? (e) => i(e, { ...b.userNode }) : void 0, B = a ? (e) => a(e, { ...b.userNode }) : void 0, te = o ? (e) => o(e, { ...b.userNode }) : void 0, ne = (n) => {
		let { selectNodesOnDrag: r, nodeDragThreshold: i } = A.getState();
		D && (!r || !E || i > 0) && Cl({
			id: e,
			store: A,
			nodeRef: M
		}), t && t(n, { ...b.userNode });
	}, re = (t) => {
		if (!(yo(t.nativeEvent) || m)) {
			if (_a.includes(t.key) && D) {
				let n = t.key === "Escape";
				Cl({
					id: e,
					store: A,
					unselect: n,
					nodeRef: M
				});
			} else if (E && y.selected && Object.prototype.hasOwnProperty.call(Hl, t.key)) {
				t.preventDefault();
				let { ariaLabelConfig: e } = A.getState();
				A.setState({ ariaLiveMessage: e["node.a11yDescription.ariaLiveMessage"]({
					direction: t.key.replace("Arrow", "").toLowerCase(),
					x: ~~b.positionAbsolute.x,
					y: ~~b.positionAbsolute.y
				}) }), P({
					direction: Hl[t.key],
					factor: t.shiftKey ? 4 : 1
				});
			}
		}
	}, ie = () => {
		if (m || !M.current?.matches(":focus-visible")) return;
		let { transform: t, width: n, height: r, autoPanOnNodeFocus: i, setCenter: a } = A.getState();
		i && (Ma(/* @__PURE__ */ new Map([[e, y]]), {
			x: 0,
			y: 0,
			width: n,
			height: r
		}, t, !0).length > 0 || a(y.position.x + F.width / 2, y.position.y + F.height / 2, { zoom: t[2] }));
	};
	return (0, x.jsx)("div", {
		className: S([
			"react-flow__node",
			`react-flow__node-${w}`,
			{ [p]: E },
			y.className,
			{
				selected: y.selected,
				selectable: D,
				parent: C,
				draggable: E,
				dragging: N
			}
		]),
		ref: M,
		style: {
			zIndex: b.z,
			transform: `translate(${b.positionAbsolute.x}px,${b.positionAbsolute.y}px)`,
			pointerEvents: ee ? "all" : "none",
			visibility: j ? "visible" : "hidden",
			...y.style,
			...I
		},
		"data-id": e,
		"data-testid": `rf__node-${e}`,
		onMouseEnter: L,
		onMouseMove: R,
		onMouseLeave: z,
		onContextMenu: B,
		onClick: ne,
		onDoubleClick: te,
		onKeyDown: k ? re : void 0,
		tabIndex: k ? 0 : void 0,
		onFocus: k ? ie : void 0,
		role: y.ariaRole ?? (k ? "group" : void 0),
		"aria-roledescription": "node",
		"aria-describedby": m ? void 0 : `${gc}-${h}`,
		"aria-label": y.ariaLabel,
		...y.domAttributes,
		children: (0, x.jsx)(Ol, {
			value: e,
			children: (0, x.jsx)(T, {
				id: e,
				data: y.data,
				type: w,
				positionAbsoluteX: b.positionAbsolute.x,
				positionAbsoluteY: b.positionAbsolute.y,
				selected: y.selected ?? !1,
				selectable: D,
				draggable: E,
				deletable: y.deletable ?? !0,
				isConnectable: O,
				sourcePosition: y.sourcePosition,
				targetPosition: y.targetPosition,
				dragging: N,
				dragHandle: y.dragHandle,
				zIndex: b.z,
				parentId: y.parentId,
				...F
			})
		})
	});
}
var ru = (0, b.memo)(nu), iu = (e) => ({
	nodesDraggable: e.nodesDraggable,
	nodesConnectable: e.nodesConnectable,
	nodesFocusable: e.nodesFocusable,
	elementsSelectable: e.elementsSelectable,
	onError: e.onError
});
function au(e) {
	let { nodesDraggable: t, nodesConnectable: n, nodesFocusable: r, elementsSelectable: i, onError: a } = Z(iu, Y), o = Ql(e.onlyRenderVisibleElements), s = eu();
	return (0, x.jsx)("div", {
		className: "react-flow__nodes",
		style: hl,
		children: o.map((o) => (0, x.jsx)(ru, {
			id: o,
			nodeTypes: e.nodeTypes,
			nodeExtent: e.nodeExtent,
			onClick: e.onNodeClick,
			onMouseEnter: e.onNodeMouseEnter,
			onMouseMove: e.onNodeMouseMove,
			onMouseLeave: e.onNodeMouseLeave,
			onContextMenu: e.onNodeContextMenu,
			onDoubleClick: e.onNodeDoubleClick,
			noDragClassName: e.noDragClassName,
			noPanClassName: e.noPanClassName,
			rfId: e.rfId,
			disableKeyboardA11y: e.disableKeyboardA11y,
			resizeObserver: s,
			nodesDraggable: t,
			nodesConnectable: n,
			nodesFocusable: r,
			elementsSelectable: i,
			nodeClickDistance: e.nodeClickDistance,
			onError: a
		}, o))
	});
}
au.displayName = "NodeRenderer";
var ou = (0, b.memo)(au);
function su(e) {
	return Z((0, b.useCallback)((t) => {
		if (!e) return t.edges.map((e) => e.id);
		let n = [];
		if (t.width && t.height) for (let e of t.edges) {
			let r = t.nodeLookup.get(e.source), i = t.nodeLookup.get(e.target);
			r && i && ko({
				sourceNode: r,
				targetNode: i,
				width: t.width,
				height: t.height,
				transform: t.transform
			}) && n.push(e.id);
		}
		return n;
	}, [e]), Y);
}
var cu = ({ color: e = "none", strokeWidth: t = 1 }) => (0, x.jsx)("polyline", {
	className: "arrow",
	style: {
		strokeWidth: t,
		...e && { stroke: e }
	},
	strokeLinecap: "round",
	fill: "none",
	strokeLinejoin: "round",
	points: "-5,-4 0,0 -5,4"
}), lu = ({ color: e = "none", strokeWidth: t = 1 }) => (0, x.jsx)("polyline", {
	className: "arrowclosed",
	style: {
		strokeWidth: t,
		...e && {
			stroke: e,
			fill: e
		}
	},
	strokeLinecap: "round",
	strokeLinejoin: "round",
	points: "-5,-4 0,0 -5,4 -5,-4"
}), uu = {
	[Ca.Arrow]: cu,
	[Ca.ArrowClosed]: lu
};
function du(e) {
	let t = Q();
	return (0, b.useMemo)(() => Object.prototype.hasOwnProperty.call(uu, e) ? uu[e] : (t.getState().onError?.("009", ha.error009(e)), null), [e]);
}
var fu = ({ id: e, type: t, color: n, width: r = 12.5, height: i = 12.5, markerUnits: a = "strokeWidth", strokeWidth: o, orient: s = "auto-start-reverse" }) => {
	let c = du(t);
	return c ? (0, x.jsx)("marker", {
		className: "react-flow__arrowhead",
		id: e,
		markerWidth: `${r}`,
		markerHeight: `${i}`,
		viewBox: "-10 -10 20 20",
		markerUnits: a,
		orient: s,
		refX: "0",
		refY: "0",
		children: (0, x.jsx)(c, {
			color: n,
			strokeWidth: o
		})
	}) : null;
}, pu = ({ defaultColor: e, rfId: t }) => {
	let n = Z((e) => e.edges), r = Z((e) => e.defaultEdgeOptions), i = (0, b.useMemo)(() => Ko(n, {
		id: t,
		defaultColor: e,
		defaultMarkerStart: r?.markerStart,
		defaultMarkerEnd: r?.markerEnd
	}), [
		n,
		r,
		t,
		e
	]);
	return i.length ? (0, x.jsx)("svg", {
		className: "react-flow__marker",
		"aria-hidden": "true",
		children: (0, x.jsx)("defs", { children: i.map((e) => (0, x.jsx)(fu, {
			id: e.id,
			type: e.type,
			color: e.color,
			width: e.width,
			height: e.height,
			markerUnits: e.markerUnits,
			strokeWidth: e.strokeWidth,
			orient: e.orient
		}, e.id)) })
	}) : null;
};
pu.displayName = "MarkerDefinitions";
var mu = (0, b.memo)(pu);
function hu({ x: e, y: t, label: n, labelStyle: r, labelShowBg: i = !0, labelBgStyle: a, labelBgPadding: o = [2, 4], labelBgBorderRadius: s = 2, children: c, className: l, ...u }) {
	let [d, f] = (0, b.useState)({
		x: 1,
		y: 0,
		width: 0,
		height: 0
	}), p = S(["react-flow__edge-textwrapper", l]), m = (0, b.useRef)(null);
	return (0, b.useEffect)(() => {
		if (m.current) {
			let e = m.current.getBBox();
			f({
				x: e.x,
				y: e.y,
				width: e.width,
				height: e.height
			});
		}
	}, [n]), n ? (0, x.jsxs)("g", {
		transform: `translate(${e - d.width / 2} ${t - d.height / 2})`,
		className: p,
		visibility: d.width ? "visible" : "hidden",
		...u,
		children: [
			i && (0, x.jsx)("rect", {
				width: d.width + 2 * o[0],
				x: -o[0],
				y: -o[1],
				height: d.height + 2 * o[1],
				className: "react-flow__edge-textbg",
				style: a,
				rx: s,
				ry: s
			}),
			(0, x.jsx)("text", {
				className: "react-flow__edge-text",
				y: d.height / 2,
				dy: "0.3em",
				ref: m,
				style: r,
				children: n
			}),
			c
		]
	}) : null;
}
hu.displayName = "EdgeText";
var gu = (0, b.memo)(hu);
function _u({ path: e, labelX: t, labelY: n, label: r, labelStyle: i, labelShowBg: a, labelBgStyle: o, labelBgPadding: s, labelBgBorderRadius: c, interactionWidth: l = 20, ...u }) {
	return (0, x.jsxs)(x.Fragment, { children: [
		(0, x.jsx)("path", {
			...u,
			d: e,
			fill: "none",
			className: S(["react-flow__edge-path", u.className])
		}),
		l ? (0, x.jsx)("path", {
			d: e,
			fill: "none",
			strokeOpacity: 0,
			strokeWidth: l,
			className: "react-flow__edge-interaction"
		}) : null,
		r && Qa(t) && Qa(n) ? (0, x.jsx)(gu, {
			x: t,
			y: n,
			label: r,
			labelStyle: i,
			labelShowBg: a,
			labelBgStyle: o,
			labelBgPadding: s,
			labelBgBorderRadius: c
		}) : null
	] });
}
function vu({ pos: e, x1: t, y1: n, x2: r, y2: i }) {
	return e === q.Left || e === q.Right ? [.5 * (t + r), n] : [t, .5 * (n + i)];
}
function yu({ sourceX: e, sourceY: t, sourcePosition: n = q.Bottom, targetX: r, targetY: i, targetPosition: a = q.Top }) {
	let [o, s] = vu({
		pos: n,
		x1: e,
		y1: t,
		x2: r,
		y2: i
	}), [c, l] = vu({
		pos: a,
		x1: r,
		y1: i,
		x2: e,
		y2: t
	}), [u, d, f, p] = Co({
		sourceX: e,
		sourceY: t,
		targetX: r,
		targetY: i,
		sourceControlX: o,
		sourceControlY: s,
		targetControlX: c,
		targetControlY: l
	});
	return [
		`M${e},${t} C${o},${s} ${c},${l} ${r},${i}`,
		u,
		d,
		f,
		p
	];
}
function bu(e) {
	return (0, b.memo)(({ id: t, sourceX: n, sourceY: r, targetX: i, targetY: a, sourcePosition: o, targetPosition: s, label: c, labelStyle: l, labelShowBg: u, labelBgStyle: d, labelBgPadding: f, labelBgBorderRadius: p, style: m, markerEnd: h, markerStart: g, interactionWidth: _ }) => {
		let [v, y, b] = yu({
			sourceX: n,
			sourceY: r,
			sourcePosition: o,
			targetX: i,
			targetY: a,
			targetPosition: s
		});
		return (0, x.jsx)(_u, {
			id: e.isInternal ? void 0 : t,
			path: v,
			labelX: y,
			labelY: b,
			label: c,
			labelStyle: l,
			labelShowBg: u,
			labelBgStyle: d,
			labelBgPadding: f,
			labelBgBorderRadius: p,
			style: m,
			markerEnd: h,
			markerStart: g,
			interactionWidth: _
		});
	});
}
var xu = bu({ isInternal: !1 }), Su = bu({ isInternal: !0 });
xu.displayName = "SimpleBezierEdge", Su.displayName = "SimpleBezierEdgeInternal";
function Cu(e) {
	return (0, b.memo)(({ id: t, sourceX: n, sourceY: r, targetX: i, targetY: a, label: o, labelStyle: s, labelShowBg: c, labelBgStyle: l, labelBgPadding: u, labelBgBorderRadius: d, style: f, sourcePosition: p = q.Bottom, targetPosition: m = q.Top, markerEnd: h, markerStart: g, pathOptions: _, interactionWidth: v }) => {
		let [y, b, S] = zo({
			sourceX: n,
			sourceY: r,
			sourcePosition: p,
			targetX: i,
			targetY: a,
			targetPosition: m,
			borderRadius: _?.borderRadius,
			offset: _?.offset,
			stepPosition: _?.stepPosition
		});
		return (0, x.jsx)(_u, {
			id: e.isInternal ? void 0 : t,
			path: y,
			labelX: b,
			labelY: S,
			label: o,
			labelStyle: s,
			labelShowBg: c,
			labelBgStyle: l,
			labelBgPadding: u,
			labelBgBorderRadius: d,
			style: f,
			markerEnd: h,
			markerStart: g,
			interactionWidth: v
		});
	});
}
var wu = Cu({ isInternal: !1 }), Tu = Cu({ isInternal: !0 });
wu.displayName = "SmoothStepEdge", Tu.displayName = "SmoothStepEdgeInternal";
function Eu(e) {
	return (0, b.memo)(({ id: t, ...n }) => {
		let r = e.isInternal ? void 0 : t;
		return (0, x.jsx)(wu, {
			...n,
			id: r,
			pathOptions: (0, b.useMemo)(() => ({
				borderRadius: 0,
				offset: n.pathOptions?.offset
			}), [n.pathOptions?.offset])
		});
	});
}
var Du = Eu({ isInternal: !1 }), Ou = Eu({ isInternal: !0 });
Du.displayName = "StepEdge", Ou.displayName = "StepEdgeInternal";
function ku(e) {
	return (0, b.memo)(({ id: t, sourceX: n, sourceY: r, targetX: i, targetY: a, label: o, labelStyle: s, labelShowBg: c, labelBgStyle: l, labelBgPadding: u, labelBgBorderRadius: d, style: f, markerEnd: p, markerStart: m, interactionWidth: h }) => {
		let [g, _, v] = No({
			sourceX: n,
			sourceY: r,
			targetX: i,
			targetY: a
		});
		return (0, x.jsx)(_u, {
			id: e.isInternal ? void 0 : t,
			path: g,
			labelX: _,
			labelY: v,
			label: o,
			labelStyle: s,
			labelShowBg: c,
			labelBgStyle: l,
			labelBgPadding: u,
			labelBgBorderRadius: d,
			style: f,
			markerEnd: p,
			markerStart: m,
			interactionWidth: h
		});
	});
}
var Au = ku({ isInternal: !1 }), ju = ku({ isInternal: !0 });
Au.displayName = "StraightEdge", ju.displayName = "StraightEdgeInternal";
function Mu(e) {
	return (0, b.memo)(({ id: t, sourceX: n, sourceY: r, targetX: i, targetY: a, sourcePosition: o = q.Bottom, targetPosition: s = q.Top, label: c, labelStyle: l, labelShowBg: u, labelBgStyle: d, labelBgPadding: f, labelBgBorderRadius: p, style: m, markerEnd: h, markerStart: g, pathOptions: _, interactionWidth: v }) => {
		let [y, b, S] = Eo({
			sourceX: n,
			sourceY: r,
			sourcePosition: o,
			targetX: i,
			targetY: a,
			targetPosition: s,
			curvature: _?.curvature
		});
		return (0, x.jsx)(_u, {
			id: e.isInternal ? void 0 : t,
			path: y,
			labelX: b,
			labelY: S,
			label: c,
			labelStyle: l,
			labelShowBg: u,
			labelBgStyle: d,
			labelBgPadding: f,
			labelBgBorderRadius: p,
			style: m,
			markerEnd: h,
			markerStart: g,
			interactionWidth: v
		});
	});
}
var Nu = Mu({ isInternal: !1 }), Pu = Mu({ isInternal: !0 });
Nu.displayName = "BezierEdge", Pu.displayName = "BezierEdgeInternal";
var Fu = {
	default: Pu,
	straight: ju,
	step: Ou,
	smoothstep: Tu,
	simplebezier: Su
}, Iu = {
	sourceX: null,
	sourceY: null,
	targetX: null,
	targetY: null,
	sourcePosition: null,
	targetPosition: null,
	zIndex: void 0
}, Lu = (e, t, n) => n === q.Left ? e - t : n === q.Right ? e + t : e, Ru = (e, t, n) => n === q.Top ? e - t : n === q.Bottom ? e + t : e, zu = "react-flow__edgeupdater";
function Bu({ position: e, centerX: t, centerY: n, radius: r = 10, onMouseDown: i, onMouseEnter: a, onMouseOut: o, type: s }) {
	return (0, x.jsx)("circle", {
		onMouseDown: i,
		onMouseEnter: a,
		onMouseOut: o,
		className: S([zu, `${zu}-${s}`]),
		cx: Lu(t, r, e),
		cy: Ru(n, r, e),
		r,
		stroke: "transparent",
		fill: "transparent"
	});
}
function Vu({ isReconnectable: e, reconnectRadius: t, edge: n, sourceX: r, sourceY: i, targetX: a, targetY: o, sourcePosition: s, targetPosition: c, onReconnect: l, onReconnectStart: u, onReconnectEnd: d, setReconnecting: f, setUpdateHover: p }) {
	let m = Q(), h = (e, t) => {
		if (e.button !== 0) return;
		let { autoPanOnConnect: r, domNode: i, connectionMode: a, connectionRadius: o, lib: s, onConnectStart: c, cancelConnection: p, nodeLookup: h, rfId: g, panBy: _, updateConnection: v } = m.getState(), y = t.type === "target";
		Es.onPointerDown(e.nativeEvent, {
			autoPanOnConnect: r,
			connectionMode: a,
			connectionRadius: o,
			domNode: i,
			handleId: t.id,
			nodeId: t.nodeId,
			nodeLookup: h,
			isTarget: y,
			edgeUpdaterType: t.type,
			lib: s,
			flowId: g,
			cancelConnection: p,
			panBy: _,
			isValidConnection: (...e) => m.getState().isValidConnection?.(...e) ?? !0,
			onConnect: (e) => l?.(n, e),
			onConnectStart: (r, i) => {
				f(!0), u?.(e, n, t.type), c?.(r, i);
			},
			onConnectEnd: (...e) => m.getState().onConnectEnd?.(...e),
			onReconnectEnd: (e, r) => {
				f(!1), d?.(e, n, t.type, r);
			},
			updateConnection: v,
			getTransform: () => m.getState().transform,
			getFromHandle: () => m.getState().connection.fromHandle,
			dragThreshold: m.getState().connectionDragThreshold,
			handleDomNode: e.currentTarget
		});
	}, g = (e) => h(e, {
		nodeId: n.target,
		id: n.targetHandle ?? null,
		type: "target"
	}), _ = (e) => h(e, {
		nodeId: n.source,
		id: n.sourceHandle ?? null,
		type: "source"
	}), v = () => p(!0), y = () => p(!1);
	return (0, x.jsxs)(x.Fragment, { children: [(e === !0 || e === "source") && (0, x.jsx)(Bu, {
		position: s,
		centerX: r,
		centerY: i,
		radius: t,
		onMouseDown: g,
		onMouseEnter: v,
		onMouseOut: y,
		type: "source"
	}), (e === !0 || e === "target") && (0, x.jsx)(Bu, {
		position: c,
		centerX: a,
		centerY: o,
		radius: t,
		onMouseDown: _,
		onMouseEnter: v,
		onMouseOut: y,
		type: "target"
	})] });
}
function Hu({ id: e, edgesFocusable: t, edgesReconnectable: n, elementsSelectable: r, onClick: i, onDoubleClick: a, onContextMenu: o, onMouseEnter: s, onMouseMove: c, onMouseLeave: l, reconnectRadius: u, onReconnect: d, onReconnectStart: f, onReconnectEnd: p, rfId: m, edgeTypes: h, noPanClassName: g, onError: _, disableKeyboardA11y: v }) {
	let y = Z((t) => t.edgeLookup.get(e)), C = Z((e) => e.defaultEdgeOptions);
	y = C ? {
		...C,
		...y
	} : y;
	let w = y.type || "default", T = h?.[w] || Fu[w];
	T === void 0 && (_?.("011", ha.error011(w)), w = "default", T = h?.default || Fu.default);
	let E = !!(y.focusable || t && y.focusable === void 0), D = d !== void 0 && (y.reconnectable || n && y.reconnectable === void 0), O = !!(y.selectable || r && y.selectable === void 0), k = (0, b.useRef)(null), [A, j] = (0, b.useState)(!1), [M, N] = (0, b.useState)(!1), P = Q(), { zIndex: F = y.zIndex, sourceX: I, sourceY: ee, targetX: L, targetY: R, sourcePosition: z, targetPosition: B } = Z((0, b.useCallback)((t) => {
		let n = t.nodeLookup.get(y.source), r = t.nodeLookup.get(y.target);
		if (!n || !r) return Iu;
		let i = Vo({
			id: e,
			sourceNode: n,
			targetNode: r,
			sourceHandle: y.sourceHandle || null,
			targetHandle: y.targetHandle || null,
			connectionMode: t.connectionMode,
			onError: _
		}), a = Oo({
			selected: y.selected,
			zIndex: y.zIndex,
			sourceNode: n,
			targetNode: r,
			elevateOnSelect: t.elevateEdgesOnSelect,
			zIndexMode: t.zIndexMode
		});
		return {
			...i || Iu,
			zIndex: a
		};
	}, [
		y.source,
		y.target,
		y.sourceHandle,
		y.targetHandle,
		y.selected,
		y.zIndex
	]), Y), te = (0, b.useMemo)(() => y.markerStart ? `url('#${Go(y.markerStart, m)}')` : void 0, [y.markerStart, m]), ne = (0, b.useMemo)(() => y.markerEnd ? `url('#${Go(y.markerEnd, m)}')` : void 0, [y.markerEnd, m]);
	if (y.hidden || I === null || ee === null || L === null || R === null) return null;
	let re = (t) => {
		let { addSelectedEdges: n, unselectNodesAndEdges: r, multiSelectionActive: a } = P.getState();
		O && (P.setState({ nodesSelectionActive: !1 }), y.selected && a ? (r({
			nodes: [],
			edges: [y]
		}), k.current?.blur()) : n([e])), i && i(t, y);
	}, ie = a ? (e) => {
		a(e, { ...y });
	} : void 0, ae = o ? (e) => {
		o(e, { ...y });
	} : void 0, oe = s ? (e) => {
		s(e, { ...y });
	} : void 0, se = c ? (e) => {
		c(e, { ...y });
	} : void 0, ce = l ? (e) => {
		l(e, { ...y });
	} : void 0;
	return (0, x.jsx)("svg", {
		style: { zIndex: F },
		children: (0, x.jsxs)("g", {
			className: S([
				"react-flow__edge",
				`react-flow__edge-${w}`,
				y.className,
				g,
				{
					selected: y.selected,
					animated: y.animated,
					inactive: !O && !i,
					updating: A,
					selectable: O
				}
			]),
			onClick: re,
			onDoubleClick: ie,
			onContextMenu: ae,
			onMouseEnter: oe,
			onMouseMove: se,
			onMouseLeave: ce,
			onKeyDown: E ? (t) => {
				if (!v && _a.includes(t.key) && O) {
					let { unselectNodesAndEdges: n, addSelectedEdges: r } = P.getState();
					t.key === "Escape" ? (k.current?.blur(), n({ edges: [y] })) : r([e]);
				}
			} : void 0,
			tabIndex: E ? 0 : void 0,
			role: y.ariaRole ?? (E ? "group" : "img"),
			"aria-roledescription": "edge",
			"data-id": e,
			"data-testid": `rf__edge-${e}`,
			"aria-label": y.ariaLabel === null ? void 0 : y.ariaLabel || `Edge from ${y.source} to ${y.target}`,
			"aria-describedby": E ? `${_c}-${m}` : void 0,
			ref: k,
			...y.domAttributes,
			children: [!M && (0, x.jsx)(T, {
				id: e,
				source: y.source,
				target: y.target,
				type: y.type,
				selected: y.selected,
				animated: y.animated,
				selectable: O,
				deletable: y.deletable ?? !0,
				label: y.label,
				labelStyle: y.labelStyle,
				labelShowBg: y.labelShowBg,
				labelBgStyle: y.labelBgStyle,
				labelBgPadding: y.labelBgPadding,
				labelBgBorderRadius: y.labelBgBorderRadius,
				sourceX: I,
				sourceY: ee,
				targetX: L,
				targetY: R,
				sourcePosition: z,
				targetPosition: B,
				data: y.data,
				style: y.style,
				sourceHandleId: y.sourceHandle,
				targetHandleId: y.targetHandle,
				markerStart: te,
				markerEnd: ne,
				pathOptions: "pathOptions" in y ? y.pathOptions : void 0,
				interactionWidth: y.interactionWidth
			}), D && (0, x.jsx)(Vu, {
				edge: y,
				isReconnectable: D,
				reconnectRadius: u,
				onReconnect: d,
				onReconnectStart: f,
				onReconnectEnd: p,
				sourceX: I,
				sourceY: ee,
				targetX: L,
				targetY: R,
				sourcePosition: z,
				targetPosition: B,
				setUpdateHover: j,
				setReconnecting: N
			})]
		})
	});
}
var Uu = (0, b.memo)(Hu), Wu = (e) => ({
	edgesFocusable: e.edgesFocusable,
	edgesReconnectable: e.edgesReconnectable,
	elementsSelectable: e.elementsSelectable,
	connectionMode: e.connectionMode,
	onError: e.onError
});
function Gu({ defaultMarkerColor: e, onlyRenderVisibleElements: t, rfId: n, edgeTypes: r, noPanClassName: i, onReconnect: a, onEdgeContextMenu: o, onEdgeMouseEnter: s, onEdgeMouseMove: c, onEdgeMouseLeave: l, onEdgeClick: u, reconnectRadius: d, onEdgeDoubleClick: f, onReconnectStart: p, onReconnectEnd: m, disableKeyboardA11y: h }) {
	let { edgesFocusable: g, edgesReconnectable: _, elementsSelectable: v, onError: y } = Z(Wu, Y), b = su(t);
	return (0, x.jsxs)("div", {
		className: "react-flow__edges",
		children: [(0, x.jsx)(mu, {
			defaultColor: e,
			rfId: n
		}), b.map((e) => (0, x.jsx)(Uu, {
			id: e,
			edgesFocusable: g,
			edgesReconnectable: _,
			elementsSelectable: v,
			noPanClassName: i,
			onReconnect: a,
			onContextMenu: o,
			onMouseEnter: s,
			onMouseMove: c,
			onMouseLeave: l,
			onClick: u,
			reconnectRadius: d,
			onDoubleClick: f,
			onReconnectStart: p,
			onReconnectEnd: m,
			rfId: n,
			onError: y,
			edgeTypes: r,
			disableKeyboardA11y: h
		}, e))]
	});
}
Gu.displayName = "EdgeRenderer";
var Ku = (0, b.memo)(Gu), qu = (e) => `translate(${e.transform[0]}px,${e.transform[1]}px) scale(${e.transform[2]})`;
function Ju({ children: e }) {
	return (0, x.jsx)("div", {
		className: "react-flow__viewport xyflow__viewport react-flow__container",
		style: { transform: Z(qu) },
		children: e
	});
}
function Yu(e) {
	let t = ul(), n = (0, b.useRef)(!1);
	(0, b.useEffect)(() => {
		!n.current && t.viewportInitialized && e && (setTimeout(() => e(t), 1), n.current = !0);
	}, [e, t.viewportInitialized]);
}
var Xu = (e) => e.panZoom?.syncViewport;
function Zu(e) {
	let t = Z(Xu), n = Q();
	return (0, b.useEffect)(() => {
		e && (t?.(e), n.setState({ transform: [
			e.x,
			e.y,
			e.zoom
		] }));
	}, [e, t]), null;
}
function Qu(e) {
	return e.connection.inProgress ? {
		...e.connection,
		to: to(e.connection.to, e.transform)
	} : { ...e.connection };
}
function $u(e) {
	return e ? (t) => e(Qu(t)) : Qu;
}
function ed(e) {
	return Z($u(e), Y);
}
var td = (e) => ({
	nodesConnectable: e.nodesConnectable,
	isValid: e.connection.isValid,
	inProgress: e.connection.inProgress,
	width: e.width,
	height: e.height
});
function nd({ containerStyle: e, style: t, type: n, component: r }) {
	let { nodesConnectable: i, width: a, height: o, isValid: s, inProgress: c } = Z(td, Y);
	return a && i && c ? (0, x.jsx)("svg", {
		style: e,
		width: a,
		height: o,
		className: "react-flow__connectionline react-flow__container",
		children: (0, x.jsx)("g", {
			className: S(["react-flow__connection", Ta(s)]),
			children: (0, x.jsx)(rd, {
				style: t,
				type: n,
				CustomComponent: r,
				isValid: s
			})
		})
	}) : null;
}
var rd = ({ style: e, type: t = K.Bezier, CustomComponent: n, isValid: r }) => {
	let { inProgress: i, from: a, fromNode: o, fromHandle: s, fromPosition: c, to: l, toNode: u, toHandle: d, toPosition: f, pointer: p } = ed();
	if (!i) return;
	if (n) return (0, x.jsx)(n, {
		connectionLineType: t,
		connectionLineStyle: e,
		fromNode: o,
		fromHandle: s,
		fromX: a.x,
		fromY: a.y,
		toX: l.x,
		toY: l.y,
		fromPosition: c,
		toPosition: f,
		connectionStatus: Ta(r),
		toNode: u,
		toHandle: d,
		pointer: p
	});
	let m = "", h = {
		sourceX: a.x,
		sourceY: a.y,
		sourcePosition: c,
		targetX: l.x,
		targetY: l.y,
		targetPosition: f
	};
	switch (t) {
		case K.Bezier:
			[m] = Eo(h);
			break;
		case K.SimpleBezier:
			[m] = yu(h);
			break;
		case K.Step:
			[m] = zo({
				...h,
				borderRadius: 0
			});
			break;
		case K.SmoothStep:
			[m] = zo(h);
			break;
		default: [m] = No(h);
	}
	return (0, x.jsx)("path", {
		d: m,
		fill: "none",
		className: "react-flow__connection-path",
		style: e
	});
};
rd.displayName = "ConnectionLine";
var id = {};
function ad(e = id) {
	(0, b.useRef)(e), Q(), (0, b.useEffect)(() => {}, [e]);
}
function od() {
	Q(), (0, b.useRef)(!1), (0, b.useEffect)(() => {}, []);
}
function sd({ nodeTypes: e, edgeTypes: t, onInit: n, onNodeClick: r, onEdgeClick: i, onNodeDoubleClick: a, onEdgeDoubleClick: o, onNodeMouseEnter: s, onNodeMouseMove: c, onNodeMouseLeave: l, onNodeContextMenu: u, onSelectionContextMenu: d, onSelectionStart: f, onSelectionEnd: p, connectionLineType: m, connectionLineStyle: h, connectionLineComponent: g, connectionLineContainerStyle: _, selectionKeyCode: v, selectionOnDrag: y, selectionMode: b, multiSelectionKeyCode: S, panActivationKeyCode: C, zoomActivationKeyCode: w, deleteKeyCode: T, onlyRenderVisibleElements: E, elementsSelectable: D, defaultViewport: O, translateExtent: k, minZoom: A, maxZoom: j, preventScrolling: M, defaultMarkerColor: N, zoomOnScroll: P, zoomOnPinch: F, panOnScroll: I, panOnScrollSpeed: ee, panOnScrollMode: L, zoomOnDoubleClick: R, panOnDrag: z, autoPanOnSelection: B, onPaneClick: te, onPaneMouseEnter: ne, onPaneMouseMove: re, onPaneMouseLeave: ie, onPaneScroll: ae, onPaneContextMenu: oe, paneClickDistance: se, nodeClickDistance: ce, onEdgeContextMenu: le, onEdgeMouseEnter: ue, onEdgeMouseMove: de, onEdgeMouseLeave: fe, reconnectRadius: pe, onReconnect: me, onReconnectStart: he, onReconnectEnd: ge, noDragClassName: _e, noWheelClassName: ve, noPanClassName: ye, disableKeyboardA11y: be, nodeExtent: xe, rfId: Se, viewport: Ce, onViewportChange: we }) {
	return ad(e), ad(t), od(), Yu(n), Zu(Ce), (0, x.jsx)(Xl, {
		onPaneClick: te,
		onPaneMouseEnter: ne,
		onPaneMouseMove: re,
		onPaneMouseLeave: ie,
		onPaneContextMenu: oe,
		onPaneScroll: ae,
		paneClickDistance: se,
		deleteKeyCode: T,
		selectionKeyCode: v,
		selectionOnDrag: y,
		selectionMode: b,
		onSelectionStart: f,
		onSelectionEnd: p,
		multiSelectionKeyCode: S,
		panActivationKeyCode: C,
		zoomActivationKeyCode: w,
		elementsSelectable: D,
		zoomOnScroll: P,
		zoomOnPinch: F,
		zoomOnDoubleClick: R,
		panOnScroll: I,
		panOnScrollSpeed: ee,
		panOnScrollMode: L,
		panOnDrag: z,
		autoPanOnSelection: B,
		defaultViewport: O,
		translateExtent: k,
		minZoom: A,
		maxZoom: j,
		onSelectionContextMenu: d,
		preventScrolling: M,
		noDragClassName: _e,
		noWheelClassName: ve,
		noPanClassName: ye,
		disableKeyboardA11y: be,
		onViewportChange: we,
		isControlledViewport: !!Ce,
		children: (0, x.jsxs)(Ju, { children: [
			(0, x.jsx)(Ku, {
				edgeTypes: t,
				onEdgeClick: i,
				onEdgeDoubleClick: o,
				onReconnect: me,
				onReconnectStart: he,
				onReconnectEnd: ge,
				onlyRenderVisibleElements: E,
				onEdgeContextMenu: le,
				onEdgeMouseEnter: ue,
				onEdgeMouseMove: de,
				onEdgeMouseLeave: fe,
				reconnectRadius: pe,
				defaultMarkerColor: N,
				noPanClassName: ye,
				disableKeyboardA11y: be,
				rfId: Se
			}),
			(0, x.jsx)(nd, {
				style: h,
				type: m,
				component: g,
				containerStyle: _
			}),
			(0, x.jsx)("div", { className: "react-flow__edgelabel-renderer" }),
			(0, x.jsx)(ou, {
				nodeTypes: e,
				onNodeClick: r,
				onNodeDoubleClick: a,
				onNodeMouseEnter: s,
				onNodeMouseMove: c,
				onNodeMouseLeave: l,
				onNodeContextMenu: u,
				nodeClickDistance: ce,
				onlyRenderVisibleElements: E,
				noPanClassName: ye,
				noDragClassName: _e,
				disableKeyboardA11y: be,
				nodeExtent: xe,
				rfId: Se
			}),
			(0, x.jsx)("div", { className: "react-flow__viewport-portal" })
		] })
	});
}
sd.displayName = "GraphView";
var cd = (0, b.memo)(sd), ld = $a("React Flow", "https://reactflow.dev/"), ud = ({ nodes: e, edges: t, defaultNodes: n, defaultEdges: r, width: i, height: a, fitView: o, fitViewOptions: s, minZoom: c = .5, maxZoom: l = 2, nodeOrigin: u, nodeExtent: d, zIndexMode: f = "basic" } = {}) => {
	let p = /* @__PURE__ */ new Map(), m = /* @__PURE__ */ new Map(), h = /* @__PURE__ */ new Map(), g = /* @__PURE__ */ new Map(), _ = r ?? t ?? [], v = n ?? e ?? [], y = u ?? [0, 0], b = d ?? ga;
	us(h, g, _);
	let { nodesInitialized: x } = ts(v, p, m, {
		nodeOrigin: y,
		nodeExtent: b,
		zIndexMode: f
	}), S = [
		0,
		0,
		1
	];
	if (o && i && a) {
		let { x: e, y: t, zoom: n } = oo(ja(p, { filter: (e) => !!((e.width || e.initialWidth) && (e.height || e.initialHeight)) }), i, a, c, l, s?.padding ?? .1);
		S = [
			e,
			t,
			n
		];
	}
	return {
		rfId: "1",
		width: i ?? 0,
		height: a ?? 0,
		transform: S,
		nodes: v,
		nodesInitialized: x,
		nodeLookup: p,
		parentLookup: m,
		edges: _,
		edgeLookup: g,
		connectionLookup: h,
		onNodesChange: null,
		onEdgesChange: null,
		hasDefaultNodes: n !== void 0,
		hasDefaultEdges: r !== void 0,
		panZoom: null,
		minZoom: c,
		maxZoom: l,
		translateExtent: ga,
		nodeExtent: b,
		nodesSelectionActive: !1,
		userSelectionActive: !1,
		userSelectionRect: null,
		connectionMode: ya.Strict,
		domNode: null,
		paneDragging: !1,
		noPanClassName: "nopan",
		nodeOrigin: y,
		nodeDragThreshold: 1,
		connectionDragThreshold: 1,
		snapGrid: [15, 15],
		snapToGrid: !1,
		nodesDraggable: !0,
		nodesConnectable: !0,
		nodesFocusable: !0,
		edgesFocusable: !0,
		edgesReconnectable: !0,
		elementsSelectable: !0,
		elevateNodesOnSelect: !0,
		elevateEdgesOnSelect: !0,
		selectNodesOnDrag: !0,
		multiSelectionActive: !1,
		fitViewQueued: o ?? !1,
		fitViewOptions: s,
		fitViewResolver: null,
		connection: { ...Sa },
		connectionClickStartHandle: null,
		connectOnClick: !0,
		ariaLiveMessage: "",
		autoPanOnConnect: !0,
		autoPanOnNodeDrag: !0,
		autoPanOnNodeFocus: !0,
		autoPanSpeed: 15,
		connectionRadius: 20,
		onError: ld,
		isValidConnection: void 0,
		onSelectionChangeHandlers: [],
		lib: "react",
		debug: !1,
		ariaLabelConfig: va,
		zIndexMode: f,
		onNodesChangeMiddlewareMap: /* @__PURE__ */ new Map(),
		onEdgesChangeMiddlewareMap: /* @__PURE__ */ new Map()
	};
}, dd = ({ nodes: e, edges: t, defaultNodes: n, defaultEdges: r, width: i, height: a, fitView: o, fitViewOptions: s, minZoom: c, maxZoom: l, nodeOrigin: u, nodeExtent: d, zIndexMode: f }) => dc((p, m) => {
	async function h() {
		let { nodeLookup: e, panZoom: t, fitViewOptions: n, fitViewResolver: r, width: i, height: a, minZoom: o, maxZoom: s } = m();
		t && (await Fa({
			nodes: e,
			width: i,
			height: a,
			panZoom: t,
			minZoom: o,
			maxZoom: s
		}, n), r?.resolve(!0), p({ fitViewResolver: null }));
	}
	return {
		...ud({
			nodes: e,
			edges: t,
			width: i,
			height: a,
			fitView: o,
			fitViewOptions: s,
			minZoom: c,
			maxZoom: l,
			nodeOrigin: u,
			nodeExtent: d,
			defaultNodes: n,
			defaultEdges: r,
			zIndexMode: f
		}),
		setNodes: (e) => {
			let { nodeLookup: t, parentLookup: n, nodeOrigin: r, elevateNodesOnSelect: i, fitViewQueued: a, zIndexMode: o, nodesSelectionActive: s } = m(), { nodesInitialized: c, hasSelectedNodes: l } = ts(e, t, n, {
				nodeOrigin: r,
				nodeExtent: d,
				elevateNodesOnSelect: i,
				checkEquality: !0,
				zIndexMode: o
			}), u = s && l;
			a && c ? (h(), p({
				nodes: e,
				nodesInitialized: c,
				fitViewQueued: !1,
				fitViewOptions: void 0,
				nodesSelectionActive: u
			})) : p({
				nodes: e,
				nodesInitialized: c,
				nodesSelectionActive: u
			});
		},
		setEdges: (e) => {
			let { connectionLookup: t, edgeLookup: n } = m();
			us(t, n, e), p({ edges: e });
		},
		setDefaultNodesAndEdges: (e, t) => {
			if (e) {
				let { setNodes: t } = m();
				t(e), p({ hasDefaultNodes: !0 });
			}
			if (t) {
				let { setEdges: e } = m();
				e(t), p({ hasDefaultEdges: !0 });
			}
		},
		updateNodeInternals: (e) => {
			let { triggerNodeChanges: t, nodeLookup: n, parentLookup: r, domNode: i, nodeOrigin: a, nodeExtent: o, debug: s, fitViewQueued: c, zIndexMode: l } = m(), { changes: u, updatedInternals: d } = ss(e, n, r, i, a, o, l);
			d && (Qo(n, r, {
				nodeOrigin: a,
				nodeExtent: o,
				zIndexMode: l
			}), c ? (h(), p({
				fitViewQueued: !1,
				fitViewOptions: void 0
			})) : p({}), u?.length > 0 && (s && console.log("React Flow: trigger node changes", u), t?.(u)));
		},
		updateNodePositions: (e, t = !1) => {
			let n = [], r = [], { nodeLookup: i, triggerNodeChanges: a, connection: o, updateConnection: s, onNodesChangeMiddlewareMap: c } = m();
			for (let [a, c] of e) {
				let e = i.get(a), l = !!(e?.expandParent && e?.parentId && c?.position), u = {
					id: a,
					type: "position",
					position: l ? {
						x: Math.max(0, c.position.x),
						y: Math.max(0, c.position.y)
					} : c.position,
					dragging: t
				};
				if (e && o.inProgress && o.fromNode.id === e.id) {
					let t = Uo(e, o.fromHandle, q.Left, !0);
					s({
						...o,
						from: t
					});
				}
				l && e.parentId && n.push({
					id: a,
					parentId: e.parentId,
					rect: {
						...c.internals.positionAbsolute,
						width: c.measured.width ?? 0,
						height: c.measured.height ?? 0
					}
				}), r.push(u);
			}
			if (n.length > 0) {
				let { parentLookup: e, nodeOrigin: t } = m(), a = os(n, i, e, t);
				r.push(...a);
			}
			for (let e of c.values()) r = e(r);
			a(r);
		},
		triggerNodeChanges: (e) => {
			let { onNodesChange: t, setNodes: n, nodes: r, hasDefaultNodes: i, debug: a } = m();
			e?.length && (i && n(Kc(e, r)), a && console.log("React Flow: trigger node changes", e), t?.(e));
		},
		triggerEdgeChanges: (e) => {
			let { onEdgesChange: t, setEdges: n, edges: r, hasDefaultEdges: i, debug: a } = m();
			e?.length && (i && n(qc(e, r)), a && console.log("React Flow: trigger edge changes", e), t?.(e));
		},
		addSelectedNodes: (e) => {
			let { multiSelectionActive: t, edgeLookup: n, nodeLookup: r, triggerNodeChanges: i, triggerEdgeChanges: a } = m();
			if (t) {
				i(e.map((e) => Jc(e, !0)));
				return;
			}
			i(Yc(r, /* @__PURE__ */ new Set([...e]), !0)), a(Yc(n));
		},
		addSelectedEdges: (e) => {
			let { multiSelectionActive: t, edgeLookup: n, nodeLookup: r, triggerNodeChanges: i, triggerEdgeChanges: a } = m();
			if (t) {
				a(e.map((e) => Jc(e, !0)));
				return;
			}
			a(Yc(n, /* @__PURE__ */ new Set([...e]))), i(Yc(r, /* @__PURE__ */ new Set(), !0));
		},
		unselectNodesAndEdges: ({ nodes: e, edges: t } = {}) => {
			let { edges: n, nodes: r, nodeLookup: i, triggerNodeChanges: a, triggerEdgeChanges: o } = m(), s = e || r, c = t || n, l = [];
			for (let e of s) {
				if (!e.selected) continue;
				let t = i.get(e.id);
				t && (t.selected = !1), l.push(Jc(e.id, !1));
			}
			let u = [];
			for (let e of c) e.selected && u.push(Jc(e.id, !1));
			a(l), o(u);
		},
		setMinZoom: (e) => {
			let { panZoom: t, maxZoom: n } = m();
			t?.setScaleExtent([e, n]), p({ minZoom: e });
		},
		setMaxZoom: (e) => {
			let { panZoom: t, minZoom: n } = m();
			t?.setScaleExtent([n, e]), p({ maxZoom: e });
		},
		setTranslateExtent: (e) => {
			m().panZoom?.setTranslateExtent(e), p({ translateExtent: e });
		},
		resetSelectedElements: () => {
			let { edges: e, nodes: t, triggerNodeChanges: n, triggerEdgeChanges: r, elementsSelectable: i } = m();
			if (!i) return;
			let a = t.reduce((e, t) => t.selected ? [...e, Jc(t.id, !1)] : e, []), o = e.reduce((e, t) => t.selected ? [...e, Jc(t.id, !1)] : e, []);
			n(a), r(o);
		},
		setNodeExtent: (e) => {
			let { nodes: t, nodeLookup: n, parentLookup: r, nodeOrigin: i, elevateNodesOnSelect: a, nodeExtent: o, zIndexMode: s } = m();
			e[0][0] === o[0][0] && e[0][1] === o[0][1] && e[1][0] === o[1][0] && e[1][1] === o[1][1] || (ts(t, n, r, {
				nodeOrigin: i,
				nodeExtent: e,
				elevateNodesOnSelect: a,
				checkEquality: !1,
				zIndexMode: s
			}), p({ nodeExtent: e }));
		},
		panBy: (e) => {
			let { transform: t, width: n, height: r, panZoom: i, translateExtent: a } = m();
			return cs({
				delta: e,
				panZoom: i,
				transform: t,
				translateExtent: a,
				width: n,
				height: r
			});
		},
		setCenter: async (e, t, n) => {
			let { width: r, height: i, maxZoom: a, panZoom: o } = m();
			if (!o) return !1;
			let s = n?.zoom === void 0 ? a : n.zoom;
			return await o.setViewport({
				x: r / 2 - e * s,
				y: i / 2 - t * s,
				zoom: s
			}, {
				duration: n?.duration,
				ease: n?.ease,
				interpolate: n?.interpolate
			}), !0;
		},
		cancelConnection: () => {
			p({ connection: { ...Sa } });
		},
		updateConnection: (e) => {
			p({ connection: e });
		},
		reset: () => p({ ...ud() })
	};
}, Object.is);
function fd({ initialNodes: e, initialEdges: t, defaultNodes: n, defaultEdges: r, initialWidth: i, initialHeight: a, initialMinZoom: o, initialMaxZoom: s, initialFitViewOptions: c, fitView: l, nodeOrigin: u, nodeExtent: d, zIndexMode: f, children: p }) {
	let [m] = (0, b.useState)(() => dd({
		nodes: e,
		edges: t,
		defaultNodes: n,
		defaultEdges: r,
		width: i,
		height: a,
		fitView: l,
		minZoom: o,
		maxZoom: s,
		fitViewOptions: c,
		nodeOrigin: u,
		nodeExtent: d,
		zIndexMode: f
	}));
	return (0, x.jsx)(pc, {
		value: m,
		children: (0, x.jsx)(sl, { children: (0, x.jsx)(Ml, { children: p }) })
	});
}
function pd({ children: e, nodes: t, edges: n, defaultNodes: r, defaultEdges: i, width: a, height: o, fitView: s, fitViewOptions: c, minZoom: l, maxZoom: u, nodeOrigin: d, nodeExtent: f, zIndexMode: p }) {
	return (0, b.useContext)(fc) ? (0, x.jsx)(x.Fragment, { children: e }) : (0, x.jsx)(fd, {
		initialNodes: t,
		initialEdges: n,
		defaultNodes: r,
		defaultEdges: i,
		initialWidth: a,
		initialHeight: o,
		fitView: s,
		initialFitViewOptions: c,
		initialMinZoom: l,
		initialMaxZoom: u,
		nodeOrigin: d,
		nodeExtent: f,
		zIndexMode: p,
		children: e
	});
}
var md = {
	width: "100%",
	height: "100%",
	overflow: "hidden",
	position: "relative",
	zIndex: 0
};
function hd({ nodes: e, edges: t, defaultNodes: n, defaultEdges: r, className: i, nodeTypes: a, edgeTypes: o, onNodeClick: s, onEdgeClick: c, onInit: l, onMove: u, onMoveStart: d, onMoveEnd: f, onConnect: p, onConnectStart: m, onConnectEnd: h, onClickConnectStart: g, onClickConnectEnd: _, onNodeMouseEnter: v, onNodeMouseMove: y, onNodeMouseLeave: C, onNodeContextMenu: w, onNodeDoubleClick: T, onNodeDragStart: E, onNodeDrag: D, onNodeDragStop: O, onNodesDelete: k, onEdgesDelete: A, onDelete: j, onSelectionChange: M, onSelectionDragStart: N, onSelectionDrag: P, onSelectionDragStop: F, onSelectionContextMenu: I, onSelectionStart: ee, onSelectionEnd: L, onBeforeDelete: R, connectionMode: z, connectionLineType: B = K.Bezier, connectionLineStyle: te, connectionLineComponent: ne, connectionLineContainerStyle: re, deleteKeyCode: ie = "Backspace", selectionKeyCode: ae = "Shift", selectionOnDrag: oe = !1, selectionMode: se = xa.Full, panActivationKeyCode: ce = "Space", multiSelectionKeyCode: le = so() ? "Meta" : "Control", zoomActivationKeyCode: ue = so() ? "Meta" : "Control", snapToGrid: de, snapGrid: fe, onlyRenderVisibleElements: pe = !1, selectNodesOnDrag: me, nodesDraggable: he, autoPanOnNodeFocus: ge, nodesConnectable: _e, nodesFocusable: ve, nodeOrigin: ye = Mc, edgesFocusable: be, edgesReconnectable: xe, elementsSelectable: Se = !0, defaultViewport: Ce = Nc, minZoom: we = .5, maxZoom: Te = 2, translateExtent: Ee = ga, preventScrolling: De = !0, nodeExtent: Oe, defaultMarkerColor: ke = "#b1b1b7", zoomOnScroll: Ae = !0, zoomOnPinch: je = !0, panOnScroll: Me = !1, panOnScrollSpeed: Ne = .5, panOnScrollMode: Pe = ba.Free, zoomOnDoubleClick: Fe = !0, panOnDrag: Ie = !0, onPaneClick: Le, onPaneMouseEnter: Re, onPaneMouseMove: ze, onPaneMouseLeave: Be, onPaneScroll: Ve, onPaneContextMenu: He, paneClickDistance: Ue = 1, nodeClickDistance: We = 0, children: Ge, onReconnect: Ke, onReconnectStart: qe, onReconnectEnd: Je, onEdgeContextMenu: Ye, onEdgeDoubleClick: Xe, onEdgeMouseEnter: Ze, onEdgeMouseMove: Qe, onEdgeMouseLeave: $e, reconnectRadius: et = 10, onNodesChange: tt, onEdgesChange: nt, noDragClassName: rt = "nodrag", noWheelClassName: it = "nowheel", noPanClassName: at = "nopan", fitView: ot, fitViewOptions: st, connectOnClick: ct, attributionPosition: lt, proOptions: ut, defaultEdgeOptions: dt, elevateNodesOnSelect: ft = !0, elevateEdgesOnSelect: pt = !1, disableKeyboardA11y: mt = !1, autoPanOnConnect: ht, autoPanOnNodeDrag: gt, autoPanOnSelection: _t = !0, autoPanSpeed: vt, connectionRadius: yt, isValidConnection: bt, onError: xt, style: St, id: Ct, nodeDragThreshold: wt, connectionDragThreshold: Tt, viewport: Et, onViewportChange: Dt, width: Ot, height: kt, colorMode: At = "light", debug: jt, onScroll: Mt, ariaLabelConfig: Nt, zIndexMode: Pt = "basic", ...Ft }, It) {
	let Lt = Ct || "1", Rt = zc(At), zt = (0, b.useCallback)((e) => {
		e.currentTarget.scrollTo({
			top: 0,
			left: 0,
			behavior: "instant"
		}), Mt?.(e);
	}, [Mt]);
	return (0, x.jsx)("div", {
		"data-testid": "rf__wrapper",
		...Ft,
		onScroll: zt,
		style: {
			...St,
			...md
		},
		ref: It,
		className: S([
			"react-flow",
			i,
			Rt
		]),
		id: Ct,
		role: "application",
		children: (0, x.jsxs)(pd, {
			nodes: e,
			edges: t,
			width: Ot,
			height: kt,
			fitView: ot,
			fitViewOptions: st,
			minZoom: we,
			maxZoom: Te,
			nodeOrigin: ye,
			nodeExtent: Oe,
			zIndexMode: Pt,
			children: [
				(0, x.jsx)(Lc, {
					nodes: e,
					edges: t,
					defaultNodes: n,
					defaultEdges: r,
					onConnect: p,
					onConnectStart: m,
					onConnectEnd: h,
					onClickConnectStart: g,
					onClickConnectEnd: _,
					nodesDraggable: he,
					autoPanOnNodeFocus: ge,
					nodesConnectable: _e,
					nodesFocusable: ve,
					edgesFocusable: be,
					edgesReconnectable: xe,
					elementsSelectable: Se,
					elevateNodesOnSelect: ft,
					elevateEdgesOnSelect: pt,
					minZoom: we,
					maxZoom: Te,
					nodeExtent: Oe,
					onNodesChange: tt,
					onEdgesChange: nt,
					snapToGrid: de,
					snapGrid: fe,
					connectionMode: z,
					translateExtent: Ee,
					connectOnClick: ct,
					defaultEdgeOptions: dt,
					fitView: ot,
					fitViewOptions: st,
					onNodesDelete: k,
					onEdgesDelete: A,
					onDelete: j,
					onNodeDragStart: E,
					onNodeDrag: D,
					onNodeDragStop: O,
					onSelectionDrag: P,
					onSelectionDragStart: N,
					onSelectionDragStop: F,
					onMove: u,
					onMoveStart: d,
					onMoveEnd: f,
					noPanClassName: at,
					nodeOrigin: ye,
					rfId: Lt,
					autoPanOnConnect: ht,
					autoPanOnNodeDrag: gt,
					autoPanSpeed: vt,
					onError: xt,
					connectionRadius: yt,
					isValidConnection: bt,
					selectNodesOnDrag: me,
					nodeDragThreshold: wt,
					connectionDragThreshold: Tt,
					onBeforeDelete: R,
					debug: jt,
					ariaLabelConfig: Nt,
					zIndexMode: Pt
				}),
				(0, x.jsx)(cd, {
					onInit: l,
					onNodeClick: s,
					onEdgeClick: c,
					onNodeMouseEnter: v,
					onNodeMouseMove: y,
					onNodeMouseLeave: C,
					onNodeContextMenu: w,
					onNodeDoubleClick: T,
					nodeTypes: a,
					edgeTypes: o,
					connectionLineType: B,
					connectionLineStyle: te,
					connectionLineComponent: ne,
					connectionLineContainerStyle: re,
					selectionKeyCode: ae,
					selectionOnDrag: oe,
					selectionMode: se,
					deleteKeyCode: ie,
					multiSelectionKeyCode: le,
					panActivationKeyCode: ce,
					zoomActivationKeyCode: ue,
					onlyRenderVisibleElements: pe,
					defaultViewport: Ce,
					translateExtent: Ee,
					minZoom: we,
					maxZoom: Te,
					preventScrolling: De,
					zoomOnScroll: Ae,
					zoomOnPinch: je,
					zoomOnDoubleClick: Fe,
					panOnScroll: Me,
					panOnScrollSpeed: Ne,
					panOnScrollMode: Pe,
					panOnDrag: Ie,
					autoPanOnSelection: _t,
					onPaneClick: Le,
					onPaneMouseEnter: Re,
					onPaneMouseMove: ze,
					onPaneMouseLeave: Be,
					onPaneScroll: Ve,
					onPaneContextMenu: He,
					paneClickDistance: Ue,
					nodeClickDistance: We,
					onSelectionContextMenu: I,
					onSelectionStart: ee,
					onSelectionEnd: L,
					onReconnect: Ke,
					onReconnectStart: qe,
					onReconnectEnd: Je,
					onEdgeContextMenu: Ye,
					onEdgeDoubleClick: Xe,
					onEdgeMouseEnter: Ze,
					onEdgeMouseMove: Qe,
					onEdgeMouseLeave: $e,
					reconnectRadius: et,
					defaultMarkerColor: ke,
					noDragClassName: rt,
					noWheelClassName: it,
					noPanClassName: at,
					rfId: Lt,
					disableKeyboardA11y: mt,
					nodeExtent: Oe,
					viewport: Et,
					onViewportChange: Dt
				}),
				(0, x.jsx)(jc, { onSelectionChange: M }),
				Ge,
				(0, x.jsx)(Tc, {
					proOptions: ut,
					position: lt
				}),
				(0, x.jsx)(Sc, {
					rfId: Lt,
					disableKeyboardA11y: mt
				})
			]
		})
	});
}
var gd = nl(hd);
ha.error014();
function _d({ dimensions: e, lineWidth: t, variant: n, className: r }) {
	return (0, x.jsx)("path", {
		strokeWidth: t,
		d: `M${e[0] / 2} 0 V${e[1]} M0 ${e[1] / 2} H${e[0]}`,
		className: S([
			"react-flow__background-pattern",
			n,
			r
		])
	});
}
function vd({ radius: e, className: t }) {
	return (0, x.jsx)("circle", {
		cx: e,
		cy: e,
		r: e,
		className: S([
			"react-flow__background-pattern",
			"dots",
			t
		])
	});
}
var yd;
(function(e) {
	e.Lines = "lines", e.Dots = "dots", e.Cross = "cross";
})(yd ||= {});
var bd = {
	[yd.Dots]: 1,
	[yd.Lines]: 1,
	[yd.Cross]: 6
}, xd = (e) => ({
	transform: e.transform,
	patternId: `pattern-${e.rfId}`
});
function Sd({ id: e, variant: t = yd.Dots, gap: n = 20, size: r, lineWidth: i = 1, offset: a = 0, color: o, bgColor: s, style: c, className: l, patternClassName: u }) {
	let d = (0, b.useRef)(null), { transform: f, patternId: p } = Z(xd, Y), m = r || bd[t], h = t === yd.Dots, g = t === yd.Cross, _ = Array.isArray(n) ? n : [n, n], v = [_[0] * f[2] || 1, _[1] * f[2] || 1], y = m * f[2], C = Array.isArray(a) ? a : [a, a], w = g ? [y, y] : v, T = [C[0] * f[2] || 1 + w[0] / 2, C[1] * f[2] || 1 + w[1] / 2], E = `${p}${e || ""}`;
	return (0, x.jsxs)("svg", {
		className: S(["react-flow__background", l]),
		style: {
			...c,
			...hl,
			"--xy-background-color-props": s,
			"--xy-background-pattern-color-props": o
		},
		ref: d,
		"data-testid": "rf__background",
		children: [(0, x.jsx)("pattern", {
			id: E,
			x: f[0] % v[0],
			y: f[1] % v[1],
			width: v[0],
			height: v[1],
			patternUnits: "userSpaceOnUse",
			patternTransform: `translate(-${T[0]},-${T[1]})`,
			children: h ? (0, x.jsx)(vd, {
				radius: y / 2,
				className: u
			}) : (0, x.jsx)(_d, {
				dimensions: w,
				lineWidth: i,
				variant: t,
				className: u
			})
		}), (0, x.jsx)("rect", {
			x: "0",
			y: "0",
			width: "100%",
			height: "100%",
			fill: `url(#${E})`
		})]
	});
}
Sd.displayName = "Background";
var Cd = (0, b.memo)(Sd);
function wd() {
	return (0, x.jsx)("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		viewBox: "0 0 32 32",
		children: (0, x.jsx)("path", { d: "M32 18.133H18.133V32h-4.266V18.133H0v-4.266h13.867V0h4.266v13.867H32z" })
	});
}
function Td() {
	return (0, x.jsx)("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		viewBox: "0 0 32 5",
		children: (0, x.jsx)("path", { d: "M0 0h32v4.2H0z" })
	});
}
function Ed() {
	return (0, x.jsx)("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		viewBox: "0 0 32 30",
		children: (0, x.jsx)("path", { d: "M3.692 4.63c0-.53.4-.938.939-.938h5.215V0H4.708C2.13 0 0 2.054 0 4.63v5.216h3.692V4.631zM27.354 0h-5.2v3.692h5.17c.53 0 .984.4.984.939v5.215H32V4.631A4.624 4.624 0 0027.354 0zm.954 24.83c0 .532-.4.94-.939.94h-5.215v3.768h5.215c2.577 0 4.631-2.13 4.631-4.707v-5.139h-3.692v5.139zm-23.677.94c-.531 0-.939-.4-.939-.94v-5.138H0v5.139c0 2.577 2.13 4.707 4.708 4.707h5.138V25.77H4.631z" })
	});
}
function Dd() {
	return (0, x.jsx)("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		viewBox: "0 0 25 32",
		children: (0, x.jsx)("path", { d: "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0 8 0 4.571 3.429 4.571 7.619v3.048H3.048A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047zm4.724-13.866H7.467V7.619c0-2.59 2.133-4.724 4.723-4.724 2.591 0 4.724 2.133 4.724 4.724v3.048z" })
	});
}
function Od() {
	return (0, x.jsx)("svg", {
		xmlns: "http://www.w3.org/2000/svg",
		viewBox: "0 0 25 32",
		children: (0, x.jsx)("path", { d: "M21.333 10.667H19.81V7.619C19.81 3.429 16.38 0 12.19 0c-4.114 1.828-1.37 2.133.305 2.438 1.676.305 4.42 2.59 4.42 5.181v3.048H3.047A3.056 3.056 0 000 13.714v15.238A3.056 3.056 0 003.048 32h18.285a3.056 3.056 0 003.048-3.048V13.714a3.056 3.056 0 00-3.048-3.047zM12.19 24.533a3.056 3.056 0 01-3.047-3.047 3.056 3.056 0 013.047-3.048 3.056 3.056 0 013.048 3.048 3.056 3.056 0 01-3.048 3.047z" })
	});
}
function kd({ children: e, className: t, ...n }) {
	return (0, x.jsx)("button", {
		type: "button",
		className: S(["react-flow__controls-button", t]),
		...n,
		children: e
	});
}
var Ad = (e) => ({
	isInteractive: e.nodesDraggable || e.nodesConnectable || e.elementsSelectable,
	minZoomReached: e.transform[2] <= e.minZoom,
	maxZoomReached: e.transform[2] >= e.maxZoom,
	ariaLabelConfig: e.ariaLabelConfig
});
function jd({ style: e, showZoom: t = !0, showFitView: n = !0, showInteractive: r = !0, fitViewOptions: i, onZoomIn: a, onZoomOut: o, onFitView: s, onInteractiveChange: c, className: l, children: u, position: d = "bottom-left", orientation: f = "vertical", "aria-label": p }) {
	let m = Q(), { isInteractive: h, minZoomReached: g, maxZoomReached: _, ariaLabelConfig: v } = Z(Ad, Y), { zoomIn: y, zoomOut: b, fitView: C } = ul();
	return (0, x.jsxs)(Cc, {
		className: S([
			"react-flow__controls",
			f === "horizontal" ? "horizontal" : "vertical",
			l
		]),
		position: d,
		style: e,
		"data-testid": "rf__controls",
		"aria-label": p ?? v["controls.ariaLabel"],
		children: [
			t && (0, x.jsxs)(x.Fragment, { children: [(0, x.jsx)(kd, {
				onClick: () => {
					y(), a?.();
				},
				className: "react-flow__controls-zoomin",
				title: v["controls.zoomIn.ariaLabel"],
				"aria-label": v["controls.zoomIn.ariaLabel"],
				disabled: _,
				children: (0, x.jsx)(wd, {})
			}), (0, x.jsx)(kd, {
				onClick: () => {
					b(), o?.();
				},
				className: "react-flow__controls-zoomout",
				title: v["controls.zoomOut.ariaLabel"],
				"aria-label": v["controls.zoomOut.ariaLabel"],
				disabled: g,
				children: (0, x.jsx)(Td, {})
			})] }),
			n && (0, x.jsx)(kd, {
				className: "react-flow__controls-fitview",
				onClick: () => {
					C(i), s?.();
				},
				title: v["controls.fitView.ariaLabel"],
				"aria-label": v["controls.fitView.ariaLabel"],
				children: (0, x.jsx)(Ed, {})
			}),
			r && (0, x.jsx)(kd, {
				className: "react-flow__controls-interactive",
				onClick: () => {
					m.setState({
						nodesDraggable: !h,
						nodesConnectable: !h,
						elementsSelectable: !h
					}), c?.(!h);
				},
				title: v["controls.interactive.ariaLabel"],
				"aria-label": v["controls.interactive.ariaLabel"],
				children: h ? (0, x.jsx)(Od, {}) : (0, x.jsx)(Dd, {})
			}),
			u
		]
	});
}
jd.displayName = "Controls";
var Md = (0, b.memo)(jd);
function Nd({ id: e, x: t, y: n, width: r, height: i, style: a, color: o, strokeColor: s, strokeWidth: c, className: l, borderRadius: u, shapeRendering: d, selected: f, onClick: p }) {
	let { background: m, backgroundColor: h } = a || {}, g = o || m || h;
	return (0, x.jsx)("rect", {
		className: S([
			"react-flow__minimap-node",
			{ selected: f },
			l
		]),
		x: t,
		y: n,
		rx: u,
		ry: u,
		width: r,
		height: i,
		style: {
			fill: g,
			stroke: s,
			strokeWidth: c
		},
		shapeRendering: d,
		onClick: p ? (t) => p(t, e) : void 0
	});
}
var Pd = (0, b.memo)(Nd), Fd = (e) => e.nodes.map((e) => e.id), Id = (e) => e instanceof Function ? e : () => e;
function Ld({ nodeStrokeColor: e, nodeColor: t, nodeClassName: n = "", nodeBorderRadius: r = 5, nodeStrokeWidth: i, nodeComponent: a = Pd, onClick: o }) {
	let s = Z(Fd, Y), c = Id(t), l = Id(e), u = Id(n), d = typeof window > "u" || window.chrome ? "crispEdges" : "geometricPrecision";
	return (0, x.jsx)(x.Fragment, { children: s.map((e) => (0, x.jsx)(zd, {
		id: e,
		nodeColorFunc: c,
		nodeStrokeColorFunc: l,
		nodeClassNameFunc: u,
		nodeBorderRadius: r,
		nodeStrokeWidth: i,
		NodeComponent: a,
		onClick: o,
		shapeRendering: d
	}, e)) });
}
function Rd({ id: e, nodeColorFunc: t, nodeStrokeColorFunc: n, nodeClassNameFunc: r, nodeBorderRadius: i, nodeStrokeWidth: a, shapeRendering: o, NodeComponent: s, onClick: c }) {
	let { node: l, x: u, y: d, width: f, height: p } = Z((t) => {
		let n = t.nodeLookup.get(e);
		if (!n) return {
			node: void 0,
			x: 0,
			y: 0,
			width: 0,
			height: 0
		};
		let r = n.internals.userNode, { x: i, y: a } = n.internals.positionAbsolute, { width: o, height: s } = lo(r);
		return {
			node: r,
			x: i,
			y: a,
			width: o,
			height: s
		};
	}, Y);
	return !l || l.hidden || !uo(l) ? null : (0, x.jsx)(s, {
		x: u,
		y: d,
		width: f,
		height: p,
		style: l.style,
		selected: !!l.selected,
		className: r(l),
		color: t(l),
		borderRadius: i,
		strokeColor: n(l),
		strokeWidth: a,
		shapeRendering: o,
		onClick: c,
		id: l.id
	});
}
var zd = (0, b.memo)(Rd), Bd = (0, b.memo)(Ld), Vd = 200, Hd = 150, Ud = (e) => !e.hidden, Wd = (e) => {
	let t = {
		x: -e.transform[0] / e.transform[2],
		y: -e.transform[1] / e.transform[2],
		width: e.width / e.transform[2],
		height: e.height / e.transform[2]
	};
	return {
		viewBB: t,
		boundingRect: e.nodeLookup.size > 0 ? Ja(ja(e.nodeLookup, { filter: Ud }), t) : t,
		rfId: e.rfId,
		panZoom: e.panZoom,
		translateExtent: e.translateExtent,
		flowWidth: e.width,
		flowHeight: e.height,
		ariaLabelConfig: e.ariaLabelConfig
	};
}, Gd = "react-flow__minimap-desc";
function Kd({ style: e, className: t, nodeStrokeColor: n, nodeColor: r, nodeClassName: i = "", nodeBorderRadius: a = 5, nodeStrokeWidth: o, nodeComponent: s, bgColor: c, maskColor: l, maskStrokeColor: u, maskStrokeWidth: d, position: f = "bottom-right", onClick: p, onNodeClick: m, pannable: h = !1, zoomable: g = !1, ariaLabel: _, inversePan: v, zoomStep: y = 1, offsetScale: C = 5 }) {
	let w = Q(), T = (0, b.useRef)(null), { boundingRect: E, viewBB: D, rfId: O, panZoom: k, translateExtent: A, flowWidth: j, flowHeight: M, ariaLabelConfig: N } = Z(Wd, Y), P = e?.width ?? Vd, F = e?.height ?? Hd, I = E.width / P, ee = E.height / F, L = Math.max(I, ee), R = L * P, z = L * F, B = C * L, te = E.x - (R - E.width) / 2 - B, ne = E.y - (z - E.height) / 2 - B, re = R + B * 2, ie = z + B * 2, ae = `${Gd}-${O}`, oe = (0, b.useRef)(0), se = (0, b.useRef)();
	oe.current = L, (0, b.useEffect)(() => {
		if (T.current && k) return se.current = Ds({
			domNode: T.current,
			panZoom: k,
			getTransform: () => w.getState().transform,
			getViewScale: () => oe.current
		}), () => {
			se.current?.destroy();
		};
	}, [k]), (0, b.useEffect)(() => {
		se.current?.update({
			translateExtent: A,
			width: j,
			height: M,
			inversePan: v,
			pannable: h,
			zoomStep: y,
			zoomable: g
		});
	}, [
		h,
		g,
		v,
		y,
		A,
		j,
		M
	]);
	let ce = p ? (e) => {
		let [t, n] = se.current?.pointer(e) || [0, 0];
		p(e, {
			x: t,
			y: n
		});
	} : void 0, le = m ? (0, b.useCallback)((e, t) => {
		let n = w.getState().nodeLookup.get(t).internals.userNode;
		m(e, n);
	}, []) : void 0, ue = _ ?? N["minimap.ariaLabel"];
	return (0, x.jsx)(Cc, {
		position: f,
		style: {
			...e,
			"--xy-minimap-background-color-props": typeof c == "string" ? c : void 0,
			"--xy-minimap-mask-background-color-props": typeof l == "string" ? l : void 0,
			"--xy-minimap-mask-stroke-color-props": typeof u == "string" ? u : void 0,
			"--xy-minimap-mask-stroke-width-props": typeof d == "number" ? d * L : void 0,
			"--xy-minimap-node-background-color-props": typeof r == "string" ? r : void 0,
			"--xy-minimap-node-stroke-color-props": typeof n == "string" ? n : void 0,
			"--xy-minimap-node-stroke-width-props": typeof o == "number" ? o : void 0
		},
		className: S(["react-flow__minimap", t]),
		"data-testid": "rf__minimap",
		children: (0, x.jsxs)("svg", {
			width: P,
			height: F,
			viewBox: `${te} ${ne} ${re} ${ie}`,
			className: "react-flow__minimap-svg",
			role: "img",
			"aria-labelledby": ae,
			ref: T,
			onClick: ce,
			children: [
				ue && (0, x.jsx)("title", {
					id: ae,
					children: ue
				}),
				(0, x.jsx)(Bd, {
					onClick: le,
					nodeColor: r,
					nodeStrokeColor: n,
					nodeBorderRadius: a,
					nodeClassName: i,
					nodeStrokeWidth: o,
					nodeComponent: s
				}),
				(0, x.jsx)("path", {
					className: "react-flow__minimap-mask",
					d: `M${te - B},${ne - B}h${re + B * 2}v${ie + B * 2}h${-re - B * 2}z
        M${D.x},${D.y}h${D.width}v${D.height}h${-D.width}z`,
					fillRule: "evenodd",
					pointerEvents: "none"
				})
			]
		})
	});
}
Kd.displayName = "MiniMap";
var qd = (0, b.memo)(Kd), Jd = (e) => (t) => e ? `${Math.max(1 / t.transform[2], 1)}` : void 0, Yd = {
	[Hs.Line]: "right",
	[Hs.Handle]: "bottom-right"
};
function Xd({ nodeId: e, position: t, variant: n = Hs.Handle, className: r, style: i = void 0, children: a, color: o, minWidth: s = 10, minHeight: c = 10, maxWidth: l = Number.MAX_VALUE, maxHeight: u = Number.MAX_VALUE, keepAspectRatio: d = !1, resizeDirection: f, autoScale: p = !0, shouldResize: m, onResizeStart: h, onResize: g, onResizeEnd: _ }) {
	let v = kl(), y = typeof e == "string" ? e : v, C = Q(), w = (0, b.useRef)(null), T = n === Hs.Handle, E = Z((0, b.useCallback)(Jd(T && p), [T, p]), Y), D = (0, b.useRef)(null), O = t ?? Yd[n];
	return (0, b.useEffect)(() => {
		if (!(!w.current || !y)) return D.current ||= $s({
			domNode: w.current,
			nodeId: y,
			getStoreItems: () => {
				let { nodeLookup: e, transform: t, snapGrid: n, snapToGrid: r, nodeOrigin: i, domNode: a } = C.getState();
				return {
					nodeLookup: e,
					transform: t,
					snapGrid: n,
					snapToGrid: r,
					nodeOrigin: i,
					paneDomNode: a
				};
			},
			onChange: (e, t) => {
				let { triggerNodeChanges: n, nodeLookup: r, parentLookup: i, nodeOrigin: a } = C.getState(), o = [], s = {
					x: e.x,
					y: e.y
				}, c = r.get(y);
				if (c && c.expandParent && c.parentId) {
					let t = c.origin ?? a, n = e.width ?? c.measured.width ?? 0, l = e.height ?? c.measured.height ?? 0, u = os([{
						id: c.id,
						parentId: c.parentId,
						rect: {
							width: n,
							height: l,
							...fo({
								x: e.x ?? c.position.x,
								y: e.y ?? c.position.y
							}, {
								width: n,
								height: l
							}, c.parentId, r, t)
						}
					}], r, i, a);
					o.push(...u), s.x = e.x ? Math.max(t[0] * n, e.x) : void 0, s.y = e.y ? Math.max(t[1] * l, e.y) : void 0;
				}
				if (s.x !== void 0 && s.y !== void 0) {
					let e = {
						id: y,
						type: "position",
						position: { ...s }
					};
					o.push(e);
				}
				if (e.width !== void 0 && e.height !== void 0) {
					let t = {
						id: y,
						type: "dimensions",
						resizing: !0,
						setAttributes: f ? f === "horizontal" ? "width" : "height" : !0,
						dimensions: {
							width: e.width,
							height: e.height
						}
					};
					o.push(t);
				}
				for (let e of t) {
					let t = {
						...e,
						type: "position"
					};
					o.push(t);
				}
				n(o);
			},
			onEnd: ({ width: e, height: t }) => {
				let n = {
					id: y,
					type: "dimensions",
					resizing: !1,
					dimensions: {
						width: e,
						height: t
					}
				};
				C.getState().triggerNodeChanges([n]);
			}
		}), D.current.update({
			controlPosition: O,
			boundaries: {
				minWidth: s,
				minHeight: c,
				maxWidth: l,
				maxHeight: u
			},
			keepAspectRatio: d,
			resizeDirection: f,
			onResizeStart: h,
			onResize: g,
			onResizeEnd: _,
			shouldResize: m
		}), () => {
			D.current?.destroy();
		};
	}, [
		O,
		s,
		c,
		l,
		u,
		d,
		h,
		g,
		_,
		m
	]), (0, x.jsx)("div", {
		className: S([
			"react-flow__resize-control",
			"nodrag",
			...O.split("-"),
			n,
			r
		]),
		ref: w,
		style: {
			...i,
			scale: E,
			...o && { [T ? "backgroundColor" : "borderColor"]: o }
		},
		children: a
	});
}
(0, b.memo)(Xd);
//#endregion
//#region src/types.ts
var Zd = {
	planned: "◇",
	queued: "⏳",
	running: "⟳",
	completed: "✓",
	failed: "✗",
	stale: "⊘",
	skipped: "−",
	blocked: "!",
	cancelled: "×",
	waiting: "⏸"
}, Qd = {
	FASTQ: {
		color: "#3b82f6",
		shape: "circle",
		label: "FASTQ"
	},
	FASTA: {
		color: "#06b6d4",
		shape: "circle",
		label: "FASTA"
	},
	GTF: {
		color: "#f59e0b",
		shape: "square",
		label: "GTF"
	},
	BED: {
		color: "#f59e0b",
		shape: "square",
		label: "BED"
	},
	BAM: {
		color: "#7c3aed",
		shape: "square",
		label: "BAM"
	},
	CRAM: {
		color: "#7c3aed",
		shape: "diamond",
		label: "CRAM"
	},
	VCF: {
		color: "#ea580c",
		shape: "triangle",
		label: "VCF"
	},
	TSV: {
		color: "#16a34a",
		shape: "diamond",
		label: "TSV"
	},
	CSV: {
		color: "#16a34a",
		shape: "square",
		label: "CSV"
	},
	counts: {
		color: "#22c55e",
		shape: "diamond",
		label: "counts"
	},
	HDF5: {
		color: "#8b5cf6",
		shape: "diamond",
		label: "HDF5"
	},
	AnnData: {
		color: "#8b5cf6",
		shape: "square",
		label: "AnnData"
	},
	PDB: {
		color: "#ec4899",
		shape: "circle",
		label: "PDB"
	},
	trees: {
		color: "#84cc16",
		shape: "triangle",
		label: "tree"
	},
	plot: {
		color: "#6b7280",
		shape: "circle",
		label: "plot"
	},
	report: {
		color: "#6b7280",
		shape: "diamond",
		label: "report"
	},
	LOG: {
		color: "#4b5563",
		shape: "circle",
		label: "log"
	},
	DIRECTORY: {
		color: "#f97316",
		shape: "square",
		label: "dir"
	},
	ANY: {
		color: "#9ca3af",
		shape: "circle",
		label: "any"
	}
};
function $d(e) {
	let t = Qd[e] || Qd.ANY, n = { background: t.color };
	switch (t.shape) {
		case "circle": return {
			...n,
			borderRadius: "50%"
		};
		case "square": return {
			...n,
			borderRadius: "2px"
		};
		case "diamond": return {
			...n,
			borderRadius: "0",
			transform: "rotate(45deg)"
		};
		case "triangle": return {
			...n,
			clipPath: "polygon(50% 0, 100% 100%, 0 100%)",
			borderRadius: "0"
		};
		default: return {
			...n,
			borderRadius: "50%"
		};
	}
}
//#endregion
//#region src/config.ts
var ef = {
	modelUrl: "http://127.0.0.1:8090/v1/chat/completions",
	modelName: "gemma4-31b-verso",
	modelMaxTokens: 4096
}, tf = typeof window < "u" && window.__BIO_CONFIG__ || {}, nf = {
	modelUrl: tf.modelUrl || ef.modelUrl,
	modelName: tf.modelName || ef.modelName,
	modelMaxTokens: tf.modelMaxTokens || ef.modelMaxTokens
};
async function rf(e, t) {
	let n = await fetch(nf.modelUrl, {
		method: "POST",
		headers: { "Content-Type": "application/json" },
		body: JSON.stringify({
			model: nf.modelName,
			messages: e,
			max_tokens: t?.maxTokens ?? nf.modelMaxTokens,
			temperature: t?.temperature ?? .3,
			min_p: t?.minP ?? .05,
			top_k: t?.topK ?? 20,
			top_p: t?.topP ?? .95
		})
	});
	if (!n.ok) throw Error(`Model API: HTTP ${n.status}`);
	return (await n.json()).choices?.[0]?.message?.content || "(no response)";
}
//#endregion
//#region src/components/LLMNode.tsx
var af = (0, b.memo)(({ data: e }) => {
	let t = e, [n, r] = (0, b.useState)(t.prompt || ""), [i, a] = (0, b.useState)(t.response || ""), [o, s] = (0, b.useState)(!1), [c, l] = (0, b.useState)(!1), [u, d] = (0, b.useState)(t.temp ?? .3), [f, p] = (0, b.useState)(t.min_p ?? .05), [m, h] = (0, b.useState)(t.top_k ?? 20), [g, _] = (0, b.useState)(t.top_p ?? .95), [v, y] = (0, b.useState)(t.max_tokens ?? 2048);
	return /* @__PURE__ */ (0, x.jsxs)("div", {
		className: "relative flex flex-col rounded-2xl border-2 border-purple-500 bg-purple-950/30",
		style: {
			width: "100%",
			height: "100%",
			minWidth: 320
		},
		children: [/* @__PURE__ */ (0, x.jsxs)("div", {
			className: "flex items-center justify-between bg-purple-900/50 px-3 py-1 text-[10px]",
			children: [/* @__PURE__ */ (0, x.jsx)("span", {
				className: "font-medium text-purple-200",
				children: "🤖 LLM Analysis"
			}), /* @__PURE__ */ (0, x.jsx)("button", {
				onClick: async (e) => {
					e.stopPropagation(), s(!0), a("");
					try {
						let e = await rf([{
							role: "system",
							content: "You are a bioinformatics analysis assistant. Interpret the following pipeline output data and answer the user's question concisely."
						}, {
							role: "user",
							content: `Pipeline output data:\n${t.collectedInputs || ""}\n\nRequest: ${n || "Summarize these results."}`
						}], {
							temperature: u,
							maxTokens: v,
							minP: f,
							topK: m,
							topP: g
						});
						a(e), t.response = e, t.prompt = n;
					} catch (e) {
						a("Error: " + e.message);
					}
					s(!1);
				},
				disabled: o,
				className: "rounded px-2 py-0.5 text-xs text-white bg-purple-600 hover:bg-purple-500 disabled:opacity-50",
				children: o ? "⟳ Thinking..." : "▶ Generate"
			})]
		}), /* @__PURE__ */ (0, x.jsxs)("div", {
			className: "flex flex-1",
			children: [
				/* @__PURE__ */ (0, x.jsx)("div", {
					className: "flex flex-col justify-center gap-3 pl-2 py-2",
					style: { minWidth: 60 },
					children: [
						1,
						2,
						3
					].map(function(e) {
						return /* @__PURE__ */ (0, x.jsxs)("div", {
							className: "flex items-center gap-1",
							children: [/* @__PURE__ */ (0, x.jsx)(Ll, {
								id: "in_" + e,
								type: "target",
								position: q.Left,
								style: {
									background: "#d1d5db",
									width: 14,
									height: 14,
									border: "2px solid #a855f7",
									borderRadius: "50%",
									position: "relative",
									transform: "none"
								}
							}), /* @__PURE__ */ (0, x.jsx)("span", {
								className: "text-[9px] text-gray-500",
								children: "any"
							})]
						}, e);
					})
				}),
				/* @__PURE__ */ (0, x.jsxs)("div", {
					className: "flex flex-1 flex-col gap-2 p-2 border-x border-purple-800/50",
					children: [
						/* @__PURE__ */ (0, x.jsxs)("div", { children: [/* @__PURE__ */ (0, x.jsx)("label", {
							className: "text-[10px] text-purple-400",
							children: "Prompt"
						}), /* @__PURE__ */ (0, x.jsx)("textarea", {
							value: n,
							onChange: (e) => r(e.target.value),
							onClick: (e) => e.stopPropagation(),
							onPointerDown: (e) => e.stopPropagation(),
							placeholder: "e.g., Summarize the QC results. Are there quality issues?",
							className: "w-full rounded bg-gray-900 px-2 py-1 text-xs text-gray-200 placeholder-gray-600 resize-none focus:outline-none focus:ring-1 focus:ring-purple-500",
							rows: 2
						})] }),
						/* @__PURE__ */ (0, x.jsxs)("div", { children: [/* @__PURE__ */ (0, x.jsxs)("button", {
							onClick: (e) => {
								e.stopPropagation(), l(!c);
							},
							className: "flex items-center gap-1 text-[10px] text-purple-400 hover:text-purple-300",
							children: [/* @__PURE__ */ (0, x.jsx)("span", { children: c ? "▾" : "▸" }), " Sampling"]
						}), c && /* @__PURE__ */ (0, x.jsxs)("div", {
							className: "mt-1 space-y-1 rounded bg-gray-900/50 p-2",
							children: [
								/* @__PURE__ */ (0, x.jsxs)("div", {
									className: "flex items-center justify-between gap-2",
									children: [/* @__PURE__ */ (0, x.jsx)("label", {
										className: "text-[10px] text-gray-400",
										children: "temperature"
									}), /* @__PURE__ */ (0, x.jsx)("input", {
										type: "number",
										step: "0.05",
										min: "0",
										max: "2",
										value: u,
										onChange: (e) => d(parseFloat(e.target.value)),
										onClick: (e) => e.stopPropagation(),
										className: "w-16 rounded bg-gray-900 px-1 py-0.5 text-[10px] text-gray-200"
									})]
								}),
								/* @__PURE__ */ (0, x.jsxs)("div", {
									className: "flex items-center justify-between gap-2",
									children: [/* @__PURE__ */ (0, x.jsx)("label", {
										className: "text-[10px] text-gray-400",
										children: "min_p"
									}), /* @__PURE__ */ (0, x.jsx)("input", {
										type: "number",
										step: "0.01",
										min: "0",
										max: "1",
										value: f,
										onChange: (e) => p(parseFloat(e.target.value)),
										onClick: (e) => e.stopPropagation(),
										className: "w-16 rounded bg-gray-900 px-1 py-0.5 text-[10px] text-gray-200"
									})]
								}),
								/* @__PURE__ */ (0, x.jsxs)("div", {
									className: "flex items-center justify-between gap-2",
									children: [/* @__PURE__ */ (0, x.jsx)("label", {
										className: "text-[10px] text-gray-400",
										children: "top_k"
									}), /* @__PURE__ */ (0, x.jsx)("input", {
										type: "number",
										step: "1",
										min: "0",
										value: m,
										onChange: (e) => h(parseInt(e.target.value)),
										onClick: (e) => e.stopPropagation(),
										className: "w-16 rounded bg-gray-900 px-1 py-0.5 text-[10px] text-gray-200"
									})]
								}),
								/* @__PURE__ */ (0, x.jsxs)("div", {
									className: "flex items-center justify-between gap-2",
									children: [/* @__PURE__ */ (0, x.jsx)("label", {
										className: "text-[10px] text-gray-400",
										children: "top_p"
									}), /* @__PURE__ */ (0, x.jsx)("input", {
										type: "number",
										step: "0.05",
										min: "0",
										max: "1",
										value: g,
										onChange: (e) => _(parseFloat(e.target.value)),
										onClick: (e) => e.stopPropagation(),
										className: "w-16 rounded bg-gray-900 px-1 py-0.5 text-[10px] text-gray-200"
									})]
								}),
								/* @__PURE__ */ (0, x.jsxs)("div", {
									className: "flex items-center justify-between gap-2",
									children: [/* @__PURE__ */ (0, x.jsx)("label", {
										className: "text-[10px] text-gray-400",
										children: "max_tokens"
									}), /* @__PURE__ */ (0, x.jsx)("input", {
										type: "number",
										step: "256",
										min: "128",
										value: v,
										onChange: (e) => y(parseInt(e.target.value)),
										onClick: (e) => e.stopPropagation(),
										className: "w-16 rounded bg-gray-900 px-1 py-0.5 text-[10px] text-gray-200"
									})]
								})
							]
						})] }),
						i && /* @__PURE__ */ (0, x.jsxs)("div", {
							className: "rounded bg-gray-900 p-2",
							children: [/* @__PURE__ */ (0, x.jsx)("label", {
								className: "text-[10px] text-purple-400",
								children: "Response"
							}), /* @__PURE__ */ (0, x.jsx)("pre", {
								className: "mt-1 max-h-40 overflow-y-auto whitespace-pre-wrap text-xs text-gray-300",
								children: i.slice(0, 1e3)
							})]
						})
					]
				}),
				/* @__PURE__ */ (0, x.jsx)("div", {
					className: "flex flex-col justify-center pr-2 py-2",
					style: { minWidth: 50 },
					children: /* @__PURE__ */ (0, x.jsxs)("div", {
						className: "flex items-center gap-1 justify-end",
						children: [/* @__PURE__ */ (0, x.jsx)("span", {
							className: "text-[9px] text-purple-300",
							children: "text"
						}), /* @__PURE__ */ (0, x.jsx)(Ll, {
							id: "out_text",
							type: "source",
							position: q.Right,
							style: {
								background: "#a855f7",
								width: 14,
								height: 14,
								border: "none",
								borderRadius: "4px"
							}
						})]
					})
				})
			]
		})]
	});
}), of = {
	qc: "#0d9488",
	alignment: "#7c3aed",
	variant: "#ea580c",
	quant: "#16a34a",
	stats: "#dc2626",
	assembly: "#2563eb",
	default: "#6b7280"
};
function sf(e) {
	let t = e.toLowerCase();
	return /(fastqc|fastp|multiqc|nanoplot)/.test(t) ? "qc" : /(star|bwa|bowtie|minimap|hisat|salmon)/.test(t) ? "alignment" : /(gatk|bcftools|freebayes|deepvariant|mutect)/.test(t) ? "variant" : /(featurecounts|htseq|kallisto)/.test(t) ? "quant" : /(deseq2|edger|limma|plink|angsd|admixture)/.test(t) ? "stats" : /(flye|hifiasm|spades|canu|racon|medaka)/.test(t) ? "assembly" : "default";
}
function cf(e) {
	return e.layout_direction === "DOWN" ? {
		target: q.Top,
		source: q.Bottom
	} : {
		target: q.Left,
		source: q.Right
	};
}
var lf = (0, b.memo)(({ data: e }) => {
	let t = e, n = t.format || t.output_ports?.[0]?.data_type || "FASTQ", r = Qd[n] || Qd.ANY, i = $d(n);
	return /* @__PURE__ */ (0, x.jsxs)("div", {
		className: "relative flex items-center justify-center",
		style: {
			width: 200,
			height: 200,
			borderRadius: "50%",
			border: `3px solid ${r.color}`,
			background: "#1e293b"
		},
		children: [/* @__PURE__ */ (0, x.jsx)(Ll, {
			type: "source",
			id: `out_${t.output_ports?.[0]?.id || "out"}`,
			position: cf(t).source,
			style: {
				...i,
				width: "14px",
				height: "14px",
				border: "none"
			}
		}), /* @__PURE__ */ (0, x.jsxs)("div", {
			className: "flex max-w-[160px] flex-col items-center text-center text-xs",
			children: [
				/* @__PURE__ */ (0, x.jsx)("div", {
					className: "text-lg",
					children: "📁"
				}),
				/* @__PURE__ */ (0, x.jsx)("div", {
					className: "w-full break-words px-1 font-bold leading-tight whitespace-normal",
					style: { color: r.color },
					title: t.label || "input",
					children: t.label || "input"
				}),
				/* @__PURE__ */ (0, x.jsx)("div", {
					className: "text-gray-500 text-[10px]",
					children: r.label
				})
			]
		})]
	});
}), uf = {
	r1: "pair1",
	r2: "pair2",
	r1_out: "pair1",
	r2_out: "pair2",
	ref: "reference",
	gtf: "annotation",
	bam: "alignment",
	bam_out: "sorted",
	bai: "index",
	sorted: "sorted",
	counts: "counts",
	metadata: "metadata",
	results: "results",
	plot: "plot",
	report: "report",
	log: "log",
	vcf: "variants",
	vcf_out: "filtered",
	assembly: "assembly",
	reads: "reads",
	sam: "alignment",
	in: "input",
	out: "output"
};
function df(e) {
	return uf[e] || e;
}
var ff = (0, b.memo)(({ id: e, data: t }) => {
	let n = t, r = of[sf(n.tool || "")], i = n.status || "planned", a = Zd[i], o = (n.sample_count || 1) > 1, s = {
		inputs: n.input_ports?.length ? n.input_ports.map((e) => ({
			id: e.id,
			type: e.data_type
		})) : [{
			id: "in",
			type: "ANY"
		}],
		outputs: n.output_ports?.length ? n.output_ports.map((e) => ({
			id: e.id,
			type: e.data_type
		})) : [{
			id: "out",
			type: "ANY"
		}]
	}, [c, l] = (0, b.useState)(!1), u = async (t, r) => {
		t.stopPropagation(), l(!0);
		try {
			await n.onRun?.(e, r);
		} catch (e) {
			n.onError?.(e);
		} finally {
			l(!1);
		}
	}, d = {
		completed: "bg-green-900 text-green-300",
		running: "bg-yellow-900 text-yellow-300 animate-pulse",
		failed: "bg-red-900 text-red-300",
		planned: "bg-gray-800 text-gray-400",
		queued: "bg-blue-900 text-blue-300",
		stale: "bg-orange-900 text-orange-300",
		skipped: "bg-gray-700 text-gray-500",
		cache_hit: "bg-emerald-900 text-emerald-300",
		blocked: "bg-red-950 text-red-300",
		cancelled: "bg-gray-700 text-gray-400",
		waiting: "bg-purple-900 text-purple-300 animate-pulse"
	}[i] || "bg-gray-800 text-gray-400", f = i, p = f === "cache_hit" ? " 💾" : "";
	return /* @__PURE__ */ (0, x.jsxs)("div", {
		className: "relative flex flex-col rounded-lg border-2 bg-[#1e293b]",
		style: {
			borderColor: n.proposalChange ? "#facc15" : r,
			boxShadow: n.proposalChange ? "0 0 0 4px rgb(250 204 21 / 25%), 0 0 24px rgb(250 204 21 / 30%)" : void 0,
			opacity: n.proposalRemoved ? .55 : 1,
			width: "100%",
			height: "100%"
		},
		title: n.description || n.label || n.tool,
		children: [/* @__PURE__ */ (0, x.jsxs)("div", {
			className: `flex items-center justify-between rounded-t-md px-2 py-0.5 text-[10px] font-medium ${d}`,
			children: [/* @__PURE__ */ (0, x.jsxs)("span", { children: [
				a,
				" ",
				f === "cache_hit" ? "cached" : i,
				p
			] }), /* @__PURE__ */ (0, x.jsxs)("div", {
				className: "flex items-center gap-1",
				children: [!!n.diagnosticCount && /* @__PURE__ */ (0, x.jsxs)("span", {
					className: n.diagnosticSeverity === "error" ? "text-red-200" : n.diagnosticSeverity === "warning" ? "text-amber-200" : "text-sky-200",
					title: `${n.diagnosticCount} run diagnostic${n.diagnosticCount === 1 ? "" : "s"}`,
					children: [
						n.diagnosticSeverity === "error" ? "⛔" : "⚠",
						" ",
						n.diagnosticCount
					]
				}), !n.readOnly && /* @__PURE__ */ (0, x.jsxs)(x.Fragment, { children: [/* @__PURE__ */ (0, x.jsx)("button", {
					onClick: (e) => u(e, !0),
					disabled: c,
					className: "rounded px-1 hover:bg-white/10 disabled:opacity-30",
					title: "Run all steps leading to this",
					children: "⏩"
				}), /* @__PURE__ */ (0, x.jsx)("button", {
					onClick: (e) => u(e, !1),
					disabled: c,
					className: "rounded px-1 hover:bg-white/10 disabled:opacity-30",
					title: "Run this step",
					children: c ? "⟳" : "▶"
				})] })]
			})]
		}), /* @__PURE__ */ (0, x.jsxs)("div", {
			className: "flex flex-1",
			children: [
				/* @__PURE__ */ (0, x.jsx)("div", {
					className: "flex flex-col justify-center gap-3 pl-2 py-2",
					style: { minWidth: 100 },
					children: s.inputs.map((e) => {
						let t = Qd[e.type] || Qd.ANY, r = $d(e.type);
						return /* @__PURE__ */ (0, x.jsxs)("div", {
							className: "relative flex items-center gap-1.5",
							children: [/* @__PURE__ */ (0, x.jsx)(Ll, {
								id: `in_${e.id}`,
								type: "target",
								position: cf(n).target,
								style: {
									...r,
									width: 12,
									height: 12,
									border: "none",
									left: -14,
									top: "50%",
									transform: "translateY(-50%)"
								}
							}), /* @__PURE__ */ (0, x.jsxs)("div", {
								className: "flex flex-col leading-tight",
								children: [/* @__PURE__ */ (0, x.jsx)("span", {
									className: "text-[10px] font-medium",
									style: { color: t.color },
									children: t.label
								}), /* @__PURE__ */ (0, x.jsx)("span", {
									className: "text-[9px] text-gray-500",
									children: df(e.id)
								})]
							})]
						}, e.id);
					})
				}),
				/* @__PURE__ */ (0, x.jsxs)("div", {
					className: "flex flex-1 flex-col justify-center items-center px-3 py-2 border-x border-gray-700/50",
					children: [
						/* @__PURE__ */ (0, x.jsx)("div", {
							className: "flex items-center gap-2",
							children: /* @__PURE__ */ (0, x.jsx)("span", {
								className: "text-sm font-bold",
								style: { color: r },
								children: n.tool || "tool"
							})
						}),
						/* @__PURE__ */ (0, x.jsx)("div", {
							className: "text-xs text-gray-300 mt-0.5",
							children: n.label || ""
						}),
						n.script && /* @__PURE__ */ (0, x.jsxs)("div", {
							className: "mt-1 max-w-[180px] truncate rounded-full bg-cyan-950 px-2 py-0.5 font-mono text-[9px] text-cyan-300",
							title: n.script.mode === "file" ? `Project script: ${n.script.path}` : `Inline ${n.script.language} script`,
							children: [
								"</>",
								" ",
								n.script.language,
								" · ",
								n.script.mode === "file" ? n.script.path : "inline source"
							]
						}),
						n.program_binding && /* @__PURE__ */ (0, x.jsxs)("div", {
							className: `mt-1 max-w-[180px] truncate rounded-full px-2 py-0.5 text-[9px] font-medium ${n.program_binding.binding_mode === "structured" ? "bg-sky-950 text-sky-300" : "bg-amber-950 text-amber-300"}`,
							title: `${n.program_binding.version_intent.kind} ${n.program_binding.version_intent.value}; resolved ${n.program_binding.resolved_version || "unresolved"}`,
							children: [
								n.program_binding.operation_id,
								" · ",
								n.program_binding.version_intent.kind === "channel" ? `${n.program_binding.version_intent.value} → ` : "",
								n.program_binding.resolved_version || n.program_binding.version_intent.value
							]
						}),
						n.description && /* @__PURE__ */ (0, x.jsx)("div", {
							className: "mt-1 max-w-[180px] overflow-hidden text-center text-[9px] leading-tight text-gray-500",
							style: {
								display: "-webkit-box",
								WebkitBoxOrient: "vertical",
								WebkitLineClamp: 2
							},
							children: n.description
						}),
						o && /* @__PURE__ */ (0, x.jsxs)("div", {
							className: "mt-1 rounded-full px-2 py-0.5 text-[10px] font-bold",
							style: {
								background: r + "33",
								color: r
							},
							children: ["×", n.sample_count]
						})
					]
				}),
				/* @__PURE__ */ (0, x.jsx)("div", {
					className: "flex flex-col justify-center gap-3 pr-2 py-2",
					style: { minWidth: 100 },
					children: s.outputs.map((e) => {
						let t = Qd[e.type] || Qd.ANY, r = $d(e.type);
						return /* @__PURE__ */ (0, x.jsxs)("div", {
							className: "relative flex items-center justify-end gap-1.5",
							children: [/* @__PURE__ */ (0, x.jsxs)("div", {
								className: "flex flex-col leading-tight text-right",
								children: [/* @__PURE__ */ (0, x.jsx)("span", {
									className: "text-[10px] font-medium",
									style: { color: t.color },
									children: t.label
								}), /* @__PURE__ */ (0, x.jsx)("span", {
									className: "text-[9px] text-gray-500",
									children: df(e.id)
								})]
							}), /* @__PURE__ */ (0, x.jsx)(Ll, {
								id: `out_${e.id}`,
								type: "source",
								position: cf(n).source,
								style: {
									...r,
									width: 12,
									height: 12,
									border: "none",
									right: -14,
									top: "50%",
									transform: "translateY(-50%)"
								}
							})]
						}, e.id);
					})
				})
			]
		})]
	});
});
function pf(e) {
	let t = Array.isArray(e.input_ports) ? e.input_ports : [];
	return t.length ? t.map((e) => ({
		id: `in_${e.id}`,
		dataType: e.data_type || e.type || "ANY"
	})) : [{
		id: "in",
		dataType: e.format || "ANY"
	}];
}
var mf = (0, b.memo)(({ data: e }) => {
	let t = e, n = Qd[t.format || "TSV"] || Qd.ANY, r = Zd[t.status] || "", i = pf(t);
	return /* @__PURE__ */ (0, x.jsxs)("div", {
		className: "relative min-w-[300px] h-full",
		children: [i.map((e, n) => /* @__PURE__ */ (0, x.jsx)(Ll, {
			type: "target",
			id: e.id,
			position: cf(t).target,
			style: {
				...$d(e.dataType),
				width: 14,
				height: 14,
				border: "none",
				top: `${(n + 1) / (i.length + 1) * 100}%`
			}
		}, e.id)), /* @__PURE__ */ (0, x.jsx)("div", {
			className: "h-full px-8 py-4",
			style: {
				background: "#1e293b",
				border: `2px solid ${n.color}`,
				clipPath: "polygon(12% 0, 88% 0, 100% 50%, 88% 100%, 12% 100%, 0 50%)"
			},
			children: /* @__PURE__ */ (0, x.jsxs)("div", {
				className: "text-center text-xs",
				children: [
					/* @__PURE__ */ (0, x.jsxs)("div", {
						className: "font-bold",
						style: { color: n.color },
						children: ["📊 ", t.label || "output"]
					}),
					/* @__PURE__ */ (0, x.jsx)("div", {
						className: "text-gray-500 text-[10px]",
						children: n.label
					}),
					/* @__PURE__ */ (0, x.jsx)("span", {
						className: "text-sm",
						children: r
					})
				]
			})
		})]
	});
}), hf = (0, b.memo)(({ data: e }) => {
	let t = e, n = t.choice?.options || t.params?.options || t.options || [], r = Array.isArray(n) ? n : Object.keys(n), i = t.choice?.default || t.params?.default || t.default;
	return /* @__PURE__ */ (0, x.jsxs)("div", {
		className: "relative flex h-full w-full items-center justify-center",
		children: [
			/* @__PURE__ */ (0, x.jsx)(Ll, {
				type: "target",
				id: "in",
				position: cf(t).target,
				style: {
					background: "#f59e0b",
					width: 14,
					height: 14,
					border: "none"
				}
			}),
			/* @__PURE__ */ (0, x.jsx)("div", { className: "absolute inset-3 rotate-45 rounded-xl border-2 border-amber-500 bg-amber-950/80" }),
			/* @__PURE__ */ (0, x.jsxs)("div", {
				className: "relative z-10 max-w-[150px] text-center",
				children: [
					/* @__PURE__ */ (0, x.jsx)("div", {
						className: "text-[10px] font-bold uppercase tracking-wide text-amber-300",
						children: "OR · choose one"
					}),
					/* @__PURE__ */ (0, x.jsx)("div", {
						className: "mt-1 text-xs font-semibold text-slate-100",
						children: t.label || "Input mode"
					}),
					/* @__PURE__ */ (0, x.jsx)("div", {
						className: "mt-1 flex flex-wrap justify-center gap-1",
						children: r.map((e) => /* @__PURE__ */ (0, x.jsx)("span", {
							className: `rounded px-1.5 py-0.5 text-[9px] ${e === i ? "bg-amber-600 text-white" : "bg-slate-800 text-slate-300"}`,
							children: e
						}, e))
					}),
					/* @__PURE__ */ (0, x.jsx)("div", {
						className: "mt-1 text-[9px] text-amber-200/70",
						children: t.choice ? "resolved before queueing" : "choice setup required"
					})
				]
			}),
			/* @__PURE__ */ (0, x.jsx)(Ll, {
				type: "source",
				id: "out",
				position: cf(t).source,
				style: {
					background: "#f59e0b",
					width: 14,
					height: 14,
					border: "none"
				}
			})
		]
	});
}), gf = (0, b.memo)(({ data: e }) => {
	let t = e, n = t.node_type === "needs_interpretation";
	return /* @__PURE__ */ (0, x.jsxs)("div", {
		className: `relative flex h-full w-full items-center justify-center rounded-xl border-2 px-4 py-3 text-center ${n ? "border-red-500 bg-red-950/80" : "border-amber-500 bg-amber-950/80"}`,
		children: [
			/* @__PURE__ */ (0, x.jsx)(Ll, {
				type: "target",
				id: "in",
				position: cf(t).target,
				style: {
					background: n ? "#ef4444" : "#f59e0b",
					width: 14,
					height: 14,
					border: "none"
				}
			}),
			/* @__PURE__ */ (0, x.jsxs)("div", { children: [/* @__PURE__ */ (0, x.jsx)("div", {
				className: "text-[10px] font-bold uppercase tracking-wide text-amber-200",
				children: n ? "Interpretation required" : t.node_type
			}), /* @__PURE__ */ (0, x.jsx)("div", {
				className: "mt-1 max-w-[180px] text-xs font-semibold text-slate-100",
				children: t.label || t.description || t.id
			})] }),
			/* @__PURE__ */ (0, x.jsx)(Ll, {
				type: "source",
				id: "out",
				position: cf(t).source,
				style: {
					background: n ? "#ef4444" : "#f59e0b",
					width: 14,
					height: 14,
					border: "none"
				}
			})
		]
	});
}), _f = {
	input: lf,
	tool: ff,
	output: mf,
	group: (0, b.memo)(({ data: e }) => {
		let t = e, n = t.collapsed || !1, r = t.childCount || 0;
		if (n) {
			let e = t.extInputs || [], n = t.extOutputs || [];
			return /* @__PURE__ */ (0, x.jsxs)("div", {
				className: "relative flex items-center gap-3 rounded-lg border-2 border-solid px-4 py-3 cursor-pointer",
				style: {
					borderColor: "#6b7280",
					background: "#374151",
					minWidth: 200
				},
				children: [
					e.map(function(e, n) {
						return /* @__PURE__ */ (0, x.jsx)(Ll, {
							id: "in_" + n,
							type: "target",
							position: cf(t).target,
							style: {
								background: "#3b82f6",
								width: 12,
								height: 12,
								top: 20 + n * 16
							}
						}, "in_" + n);
					}),
					/* @__PURE__ */ (0, x.jsx)("span", {
						className: "text-base",
						children: "📁"
					}),
					/* @__PURE__ */ (0, x.jsxs)("div", {
						className: "flex-1",
						children: [/* @__PURE__ */ (0, x.jsx)("div", {
							className: "text-sm font-bold text-gray-100",
							children: t.label || "group"
						}), /* @__PURE__ */ (0, x.jsxs)("div", {
							className: "text-xs text-gray-400",
							children: [
								r,
								" steps",
								e.length > 0 ? " · " + e.length + " in" : "",
								n.length > 0 ? " · " + n.length + " out" : "",
								" · click to expand"
							]
						})]
					}),
					n.map(function(e, n) {
						return /* @__PURE__ */ (0, x.jsx)(Ll, {
							id: "out_" + n,
							type: "source",
							position: cf(t).source,
							style: {
								background: "#16a34a",
								width: 12,
								height: 12,
								top: 20 + n * 16
							}
						}, "out_" + n);
					})
				]
			});
		}
		return /* @__PURE__ */ (0, x.jsxs)("div", {
			className: "relative h-full w-full",
			style: { pointerEvents: "none" },
			children: [
				/* @__PURE__ */ (0, x.jsx)("div", {
					className: "absolute inset-0 rounded-lg border-2 border-dashed",
					style: {
						borderColor: "#6b7280",
						background: "rgba(55, 65, 81, 0.15)"
					}
				}),
				/* @__PURE__ */ (0, x.jsx)(Ll, {
					type: "target",
					position: cf(t).target,
					style: {
						background: "#6b7280",
						top: 18,
						pointerEvents: "none"
					}
				}),
				/* @__PURE__ */ (0, x.jsx)(Ll, {
					type: "source",
					position: cf(t).source,
					style: {
						background: "#6b7280",
						top: 18,
						pointerEvents: "none"
					}
				}),
				/* @__PURE__ */ (0, x.jsxs)("div", {
					className: "absolute top-0 left-0 right-0 flex items-center justify-between rounded-t-md px-3 py-1.5 cursor-pointer",
					style: {
						background: "#374151",
						pointerEvents: "auto",
						zIndex: 1e3
					},
					children: [/* @__PURE__ */ (0, x.jsxs)("span", {
						className: "text-sm font-bold text-gray-100",
						children: ["📂 ", t.label || "group"]
					}), /* @__PURE__ */ (0, x.jsxs)("span", {
						className: "text-xs text-gray-400",
						children: [r, " steps · click to collapse"]
					})]
				})
			]
		});
	}),
	llm: af,
	choice: hf,
	approval: gf,
	debug: gf,
	needs_interpretation: gf
}, vf = /* @__PURE__ */ new Set([
	"input",
	"tool",
	"output",
	"group",
	"llm",
	"choice",
	"approval",
	"debug",
	"needs_interpretation"
]);
function yf(e) {
	let t = String(e || "").trim().toLowerCase();
	return t === "processing" || t === "process" || t === "program" ? "tool" : t === "publish" ? "output" : vf.has(t) ? t : "tool";
}
function bf(e) {
	let t = e && typeof e == "object" ? e : {}, n = t.dag && typeof t.dag == "object" ? t.dag : t;
	if (!n.nodes || typeof n.nodes != "object" || !Array.isArray(n.edges)) throw Error("Document does not contain a Verso DAG.");
	return n;
}
function xf(e) {
	let t = e.data?.nodeData || e.data || {}, n = t.tool || e.tool || e.id, r = t.label || e.label || n, i = yf(t.node_type || e.node_type || (/(input|fastq|fasta|ref)/.test(r.toLowerCase()) ? "input" : /(output|result|plot)/.test(r.toLowerCase()) ? "output" : n.toLowerCase() === "llm" ? "llm" : "tool")), a = e.position || t.position || {
		x: 0,
		y: 0
	};
	return {
		...e,
		type: i,
		position: a,
		style: {
			...i === "input" ? { width: 200 } : i === "output" ? { width: 300 } : i === "choice" ? {
				width: 230,
				height: 180
			} : { width: 480 },
			...t.proposalChange ? {
				borderRadius: 12,
				boxShadow: "0 0 0 4px rgb(250 204 21 / 30%), 0 0 24px rgb(250 204 21 / 35%)"
			} : {},
			...t.proposalRemoved ? {
				opacity: .5,
				filter: "grayscale(0.7)"
			} : {}
		},
		data: {
			...e,
			...e.data,
			...t,
			tool: n,
			label: r,
			node_type: i,
			status: t.status || e.status || "planned",
			resources: t.resources || e.resources,
			sample_count: t.sample_count || e.sample_count || 1,
			format: t.format || e.format,
			stats: t.stats || e.stats,
			group: t.group || e.group,
			input_ports: t.input_ports || e.input_ports || [],
			output_ports: t.output_ports || e.output_ports || []
		},
		_grp: t.group || e.group
	};
}
function Sf(e, t = {}) {
	return {
		nodes: Object.entries(e.nodes).map(([e, n]) => {
			let r = xf({
				id: e,
				...n
			});
			return t.readOnly ? {
				...r,
				data: {
					...r.data,
					readOnly: !0
				}
			} : r;
		}),
		edges: e.edges.map((e, t) => ({
			...e,
			id: e.id || `e-${e.source}-${e.target}-${t}`,
			sourceHandle: e.sourceHandle || (e.source_port ? `out_${e.source_port}` : void 0),
			targetHandle: e.targetHandle || (e.target_port ? `in_${e.target_port}` : void 0)
		}))
	};
}
//#endregion
//#region src/layout/workflowLayout.ts
var Cf = 150, wf = 70;
function Tf(e) {
	let t = new Set(e.nodes.map((e) => e.id)), n = /* @__PURE__ */ new Set(), r = new Map(e.nodes.map((e) => [e.id, 0])), i = e.edges.filter((e) => t.has(e.source) && t.has(e.target));
	i.forEach((e) => {
		n.add(e.source), n.add(e.target);
	});
	for (let t = 0; t < e.nodes.length; t += 1) {
		let e = !1;
		for (let t of i) {
			let n = Math.max(r.get(t.target) || 0, (r.get(t.source) || 0) + 1);
			n !== r.get(t.target) && (r.set(t.target, n), e = !0);
		}
		if (!e) break;
	}
	let a = /* @__PURE__ */ new Map();
	e.nodes.filter((e) => n.has(e.id)).forEach((e) => {
		let t = r.get(e.id) || 0;
		a.set(t, [...a.get(t) || [], e]);
	});
	let o = {}, s = 0, c = 0;
	for (let [t, n] of [...a].sort(([e], [t]) => e - t)) {
		let r = 0;
		for (let i of n.sort((e, t) => e.id.localeCompare(t.id))) e.direction === "RIGHT" ? (o[i.id] = {
			x: t * 630,
			y: r
		}, r += i.height + wf, s = Math.max(s, o[i.id].x + i.width), c = Math.max(c, r)) : (o[i.id] = {
			x: r,
			y: t * 330
		}, r += i.width + wf, s = Math.max(s, r), c = Math.max(c, o[i.id].y + i.height));
	}
	return e.nodes.filter((e) => !n.has(e.id)).sort((e, t) => e.id.localeCompare(t.id)).forEach((t, n) => {
		o[t.id] = e.direction === "RIGHT" ? {
			x: s + Cf,
			y: n * (t.height + 30)
		} : {
			x: n * (t.width + 30),
			y: c + Cf
		};
	}), {
		requestId: e.requestId,
		positions: o
	};
}
function Ef(e) {
	let t = e.data?.nodeData || e.data || {};
	if (e.type === "input") return {
		width: 200,
		height: 200
	};
	if (e.type === "output") return {
		width: 300,
		height: 130
	};
	if (e.type === "choice") return {
		width: 230,
		height: 180
	};
	let n = Math.max(t.input_ports?.length || 0, t.output_ports?.length || 0, 1);
	return {
		width: 480,
		height: Math.max(120, 72 + n * 30)
	};
}
//#endregion
//#region src/dag-viewer/DagViewer.tsx
function Df(e) {
	return !!(e && typeof e == "object" && e.schema_version === "verso-dag-demo-v1");
}
function Of(e) {
	try {
		if (Df(e)) {
			if (bf(e.initial_dag), !Array.isArray(e.events)) return "Recording events must be an array.";
			for (let t of e.events) {
				if (!t || typeof t != "object" || !Number.isFinite(t.seq) || !Number.isFinite(t.offset_ms)) return "Recording contains an invalid event.";
				bf(t.dag);
			}
			return null;
		}
		return bf(e), null;
	} catch (e) {
		return e instanceof Error ? e.message : "Invalid Verso DAG document.";
	}
}
function kf(e, t, n) {
	let r = Number.isFinite(n) ? Math.max(.25, n) : 1;
	return !e || !t ? 700 / r : Math.min(1500, Math.max(200, t.offset_ms - e.offset_ms)) / r;
}
function Af(e, t) {
	return Df(e) ? t < 0 || !e.events.length ? bf(e.initial_dag) : bf(e.events[Math.min(t, e.events.length - 1)].dag) : bf(e);
}
function jf(e, t) {
	if (!Df(e) || t < 0 || !e.events[t]) return [];
	let n = Af(e, t), r = Af(e, t - 1), i = /* @__PURE__ */ new Set();
	for (let [e, t] of Object.entries(n.nodes)) (!(e in r.nodes) || JSON.stringify(t) !== JSON.stringify(r.nodes[e])) && i.add(e);
	let a = (e) => `${e.source}|${e.target}|${e.source_port || ""}|${e.target_port || ""}`, o = new Set(r.edges.map(a)), s = new Set(n.edges.map(a));
	for (let e of n.edges) o.has(a(e)) || (i.add(String(e.source)), i.add(String(e.target)));
	for (let e of r.edges) s.has(a(e)) || (i.add(String(e.source)), i.add(String(e.target)));
	return [...i].filter((e) => e in n.nodes);
}
function Mf(e) {
	return Df(e) ? e.events.flatMap((t, n) => {
		let r = t.dag, i = Af(e, n - 1);
		return JSON.stringify(r.nodes) !== JSON.stringify(i.nodes) || JSON.stringify(r.edges) !== JSON.stringify(i.edges) ? [n] : [];
	}) : [];
}
function Nf(e) {
	let t = Sf(e, { readOnly: !0 });
	if (!(t.nodes.length > 0 && t.nodes.every((e) => e.position.x === 0 && e.position.y === 0))) return t;
	let n = Tf({
		requestId: 1,
		direction: "RIGHT",
		nodes: t.nodes.map((e) => ({
			id: e.id,
			...Ef(e),
			group: String(e.data?.group || "")
		})),
		edges: t.edges.map((e) => ({
			id: e.id,
			source: e.source,
			target: e.target
		}))
	}), r = t.nodes.map((e) => ({
		...e,
		position: n.positions[e.id] || e.position
	})), i = new Map(r.map((e) => [e.id, e])), a = /* @__PURE__ */ new Map(), o = r.filter((e) => e.type !== "input").map((e) => ({
		node: e,
		size: Ef(e)
	})), s = (e, t) => o.some(({ node: n, size: r }) => !(e.position.x + t.width + 30 <= n.position.x || n.position.x + r.width + 30 <= e.position.x || e.position.y + t.height + 30 <= n.position.y || n.position.y + r.height + 30 <= e.position.y));
	for (let e of r.filter((e) => e.type === "input")) {
		let n = t.edges.find((t) => t.source === e.id)?.target;
		n && i.has(n) && a.set(n, [...a.get(n) || [], e]);
	}
	for (let [e, t] of a) {
		let n = i.get(e), r = Ef(n);
		t.sort((e, t) => e.id.localeCompare(t.id)).forEach((e, i) => {
			let a = Ef(e), c = {
				x: n.position.x - a.width - 90,
				y: n.position.y + (r.height - a.height) / 2 + (i - (t.length - 1) / 2) * (a.height + 35)
			}, l = a.height + 35;
			e.position = [
				0,
				1,
				-1,
				2,
				-2,
				3,
				-3,
				4,
				-4
			].map((e) => ({
				x: c.x,
				y: c.y + e * l
			})).find((t) => (e.position = t, !s(e, a))) || c, o.push({
				node: e,
				size: a
			});
		});
	}
	return {
		...t,
		nodes: r
	};
}
function Pf({ document: e, autoplay: t = !1, loop: n = !1, speed: r = 1, loopDelayMs: i = 0, fitPadding: a = .25, maxZoom: o = 1, followZoom: s = 1, controls: c = !0, chrome: l = !0, startEvent: u = -1, onProgress: d, onComplete: f, onChange: p }) {
	let m = Of(e);
	return m ? /* @__PURE__ */ (0, x.jsx)("div", {
		className: "verso-viewer-message error",
		role: "alert",
		children: m
	}) : /* @__PURE__ */ (0, x.jsx)(Ff, {
		document: e,
		autoplay: t,
		loop: n,
		speed: r,
		loopDelayMs: i,
		fitPadding: a,
		maxZoom: o,
		followZoom: s,
		controls: c,
		chrome: l,
		startEvent: u,
		onProgress: d,
		onComplete: f,
		onChange: p
	});
}
function Ff({ document: e, autoplay: t = !1, loop: n = !1, speed: r = 1, loopDelayMs: i = 0, fitPadding: a = .25, maxZoom: o = 1, followZoom: s = 1, controls: c = !0, chrome: l = !0, startEvent: u = -1, onProgress: d, onComplete: f, onChange: p }) {
	let m = Df(e) ? e : null, h = () => m ? Math.min(Math.max(u, -1), m.events.length - 1) : -1, [g, _] = (0, b.useState)(h), [v, y] = (0, b.useState)(t && !!m?.events.length), [S, C] = (0, b.useState)(null), [w, T] = (0, b.useState)(""), [E, D] = (0, b.useState)(Number.isFinite(r) ? Math.max(.25, r) : 1), [O, k] = (0, b.useState)(null), A = (0, b.useRef)(null), j = (0, b.useRef)(!1), M = (0, b.useRef)(!1), N = Af(e, g), P = (0, b.useMemo)(() => Nf(N), [N]), F = (0, b.useMemo)(() => jf(e, g), [e, g]), I = (0, b.useMemo)(() => Mf(e), [e]), ee = (e) => {
		let t = I.filter((t) => t <= e).length, n = I.length;
		d?.(e, {
			stepIndex: t ? t - 1 : -1,
			stepCount: n,
			fraction: n ? t / n : 0
		});
	}, L = (0, b.useCallback)((e = 350) => {
		!O || !P.nodes.length || O.fitView({
			padding: Math.max(0, a),
			maxZoom: Math.max(.1, o),
			duration: e
		});
	}, [
		a,
		P.nodes.length,
		O,
		o
	]);
	(0, b.useEffect)(() => {
		let e = h();
		_(e), y(t && !!m?.events.length), C(null), j.current = !1, M.current = !1, ee(e);
	}, [e]), (0, b.useEffect)(() => {
		D(Number.isFinite(r) ? Math.max(.25, r) : 1);
	}, [r]), (0, b.useEffect)(() => {
		let e = h();
		_(e), C(null), j.current = !1, M.current = !1, ee(e);
	}, [u]), (0, b.useEffect)(() => {
		y(t && !!m?.events.length);
	}, [t, m]), (0, b.useEffect)(() => {
		if (!v || !m?.events.length) return;
		let e = I.find((e) => e > g);
		if (e === void 0) {
			if (n) {
				let e = window.setTimeout(() => {
					let e = h(), t = I.find((t) => t >= e) ?? e;
					_(t), ee(t), p?.({ eventIndex: t });
				}, Math.max(0, i));
				return () => window.clearTimeout(e);
			} else y(!1);
			return;
		}
		let t = window.setTimeout(() => {
			_(() => {
				let t = e;
				return j.current = !0, ee(t), p?.({ eventIndex: t }), t;
			});
		}, kf(m.events[g], m.events[e], E));
		return () => window.clearTimeout(t);
	}, [
		g,
		n,
		i,
		p,
		d,
		E,
		v,
		m,
		I
	]), (0, b.useEffect)(() => {
		!m || v || !j.current || g !== I[I.length - 1] || M.current || (M.current = !0, f?.());
	}, [
		g,
		f,
		v,
		m,
		I
	]), (0, b.useEffect)(() => {
		S && !P.nodes.some((e) => e.id === S.id) && C(null);
	}, [P.nodes, S]), (0, b.useEffect)(() => {
		if (!O || !P.nodes.length) return;
		let e = 0, t = window.requestAnimationFrame(() => {
			e = window.requestAnimationFrame(() => {
				let e = v ? P.nodes.filter((e) => F.includes(e.id)) : [];
				e.length ? O.fitView({
					nodes: e,
					padding: .65,
					maxZoom: Math.max(.1, s),
					duration: 500
				}) : (g < 0 || !j.current) && L();
			});
		});
		return () => {
			window.cancelAnimationFrame(t), window.cancelAnimationFrame(e);
		};
	}, [
		g,
		L,
		P.nodes,
		F,
		s,
		O,
		v
	]);
	let R = (e) => {
		y(!1), _(e), C(null), j.current = !0, M.current = !1, ee(e), p?.({ eventIndex: e });
	}, z = () => {
		let e = w.trim().toLowerCase();
		if (!e) return;
		let t = P.nodes.find((t) => `${t.id} ${String(t.data?.label || "")} ${String(t.data?.tool || "")}`.toLowerCase().includes(e));
		t && (C(t), p?.({
			eventIndex: g,
			nodeId: t.id
		}), O?.fitView({
			nodes: [t],
			padding: 1,
			maxZoom: 1.2,
			duration: 250
		}));
	}, B = () => {
		m?.events.length && (!v && g >= (I[I.length - 1] ?? m.events.length - 1) && (_(I[0] ?? -1), M.current = !1), y((e) => !e));
	};
	return /* @__PURE__ */ (0, x.jsxs)("div", {
		ref: A,
		className: `verso-viewer-shell ${l ? "" : "graph-only"}`,
		children: [
			l && /* @__PURE__ */ (0, x.jsxs)("header", {
				className: "verso-viewer-header",
				children: [
					/* @__PURE__ */ (0, x.jsxs)("div", { children: [/* @__PURE__ */ (0, x.jsx)("strong", { children: m?.title || N.name || "Verso DAG" }), /* @__PURE__ */ (0, x.jsxs)("span", { children: [
						P.nodes.length,
						" nodes · ",
						P.edges.length,
						" edges",
						m?.truncated ? " · recording truncated" : ""
					] })] }),
					/* @__PURE__ */ (0, x.jsxs)("div", {
						className: "verso-viewer-actions",
						children: [
							/* @__PURE__ */ (0, x.jsx)("input", {
								"aria-label": "Search nodes",
								value: w,
								onChange: (e) => T(e.target.value),
								onKeyDown: (e) => {
									e.key === "Enter" && z();
								},
								placeholder: "Search nodes…"
							}),
							/* @__PURE__ */ (0, x.jsx)("button", {
								disabled: !w.trim(),
								onClick: z,
								children: "Find"
							}),
							/* @__PURE__ */ (0, x.jsx)("button", {
								onClick: () => void A.current?.requestFullscreen().catch(() => void 0),
								children: "Fullscreen"
							})
						]
					}),
					m && /* @__PURE__ */ (0, x.jsxs)("div", {
						className: `verso-processing ${v ? "playing" : ""}`,
						children: [/* @__PURE__ */ (0, x.jsx)("i", {}), v ? "Replaying DAG history" : "History ready"]
					})
				]
			}),
			/* @__PURE__ */ (0, x.jsxs)("div", {
				className: "verso-viewer-main",
				children: [
					/* @__PURE__ */ (0, x.jsx)("div", {
						className: "verso-viewer-canvas",
						children: /* @__PURE__ */ (0, x.jsxs)(gd, {
							nodes: P.nodes,
							edges: P.edges,
							nodeTypes: _f,
							fitView: !0,
							minZoom: .1,
							nodesDraggable: !1,
							nodesConnectable: !1,
							deleteKeyCode: null,
							elementsSelectable: !0,
							onInit: k,
							onNodeClick: (e, t) => {
								C(t), p?.({
									eventIndex: g,
									nodeId: t.id
								});
							},
							children: [/* @__PURE__ */ (0, x.jsx)(Cd, {
								color: "#334155",
								gap: 24
							}), l && c && /* @__PURE__ */ (0, x.jsxs)(x.Fragment, { children: [/* @__PURE__ */ (0, x.jsx)(Md, { showInteractive: !1 }), /* @__PURE__ */ (0, x.jsx)(qd, {
								pannable: !0,
								zoomable: !0
							})] })]
						})
					}),
					!l && m && /* @__PURE__ */ (0, x.jsxs)("div", {
						className: "verso-graph-controls",
						role: "group",
						"aria-label": "DAG playback and view controls",
						children: [/* @__PURE__ */ (0, x.jsxs)("button", {
							type: "button",
							"aria-label": v ? "Pause DAG replay" : "Play DAG replay",
							"aria-pressed": !v,
							onClick: B,
							children: [/* @__PURE__ */ (0, x.jsx)("span", {
								"aria-hidden": "true",
								children: v ? "Ⅱ" : "▶"
							}), /* @__PURE__ */ (0, x.jsx)("small", { children: v ? "Pause" : "Play" })]
						}), /* @__PURE__ */ (0, x.jsxs)("button", {
							type: "button",
							"aria-label": "Reset DAG view",
							onClick: () => L(),
							children: [/* @__PURE__ */ (0, x.jsx)("span", {
								"aria-hidden": "true",
								children: "⌖"
							}), /* @__PURE__ */ (0, x.jsx)("small", { children: "Reset" })]
						})]
					}),
					l && S && /* @__PURE__ */ (0, x.jsxs)("aside", {
						className: "verso-viewer-inspector",
						children: [
							/* @__PURE__ */ (0, x.jsx)("button", {
								"aria-label": "Close inspector",
								onClick: () => C(null),
								children: "×"
							}),
							/* @__PURE__ */ (0, x.jsx)("h2", { children: String(S.data?.label || S.id) }),
							/* @__PURE__ */ (0, x.jsx)("p", { children: String(S.data?.tool || "") }),
							/* @__PURE__ */ (0, x.jsxs)("dl", { children: [
								/* @__PURE__ */ (0, x.jsx)("dt", { children: "Type" }),
								/* @__PURE__ */ (0, x.jsx)("dd", { children: String(S.data?.node_type || "") }),
								/* @__PURE__ */ (0, x.jsx)("dt", { children: "Status" }),
								/* @__PURE__ */ (0, x.jsx)("dd", { children: String(S.data?.status || "") }),
								/* @__PURE__ */ (0, x.jsx)("dt", { children: "Inputs" }),
								/* @__PURE__ */ (0, x.jsx)("dd", { children: Array.isArray(S.data?.input_ports) ? S.data.input_ports.length : 0 }),
								/* @__PURE__ */ (0, x.jsx)("dt", { children: "Outputs" }),
								/* @__PURE__ */ (0, x.jsx)("dd", { children: Array.isArray(S.data?.output_ports) ? S.data.output_ports.length : 0 })
							] })
						]
					})
				]
			}),
			m && l && c && /* @__PURE__ */ (0, x.jsxs)("footer", {
				className: "verso-viewer-history",
				children: [/* @__PURE__ */ (0, x.jsxs)("div", {
					className: "verso-playback-controls",
					children: [
						/* @__PURE__ */ (0, x.jsx)("button", {
							"aria-label": "Previous event",
							disabled: g <= -1,
							onClick: () => R(Math.max(-1, g - 1)),
							children: "‹"
						}),
						/* @__PURE__ */ (0, x.jsx)("button", {
							disabled: !m.events.length,
							onClick: B,
							children: v ? "Pause" : "Play"
						}),
						/* @__PURE__ */ (0, x.jsx)("button", {
							"aria-label": "Next event",
							disabled: g >= m.events.length - 1,
							onClick: () => R(Math.min(m.events.length - 1, g + 1)),
							children: "›"
						}),
						/* @__PURE__ */ (0, x.jsx)("input", {
							"aria-label": "DAG history",
							type: "range",
							min: -1,
							max: Math.max(-1, m.events.length - 1),
							value: g,
							disabled: !m.events.length,
							onChange: (e) => R(Number(e.target.value))
						}),
						/* @__PURE__ */ (0, x.jsx)("select", {
							"aria-label": "Playback speed",
							value: E,
							onChange: (e) => D(Number(e.target.value)),
							children: [
								.5,
								1,
								2,
								4
							].map((e) => /* @__PURE__ */ (0, x.jsxs)("option", {
								value: e,
								children: [e, "×"]
							}, e))
						}),
						/* @__PURE__ */ (0, x.jsxs)("span", { children: [
							g + 1,
							"/",
							m.events.length
						] })
					]
				}), /* @__PURE__ */ (0, x.jsx)("ol", { children: m.events.map((e, t) => /* @__PURE__ */ (0, x.jsx)("li", { children: /* @__PURE__ */ (0, x.jsxs)("button", {
					className: t === g ? "active" : "",
					onClick: () => R(t),
					children: [/* @__PURE__ */ (0, x.jsx)("span", { children: e.source }), e.description]
				}) }, `${e.seq}-${t}`)) })]
			})
		]
	});
}
//#endregion
//#region src/dag-viewer/viewer.css?inline
var If = ":host{color:#dbeafe;background:#020617;min-height:420px;font-family:Inter,ui-sans-serif,system-ui,sans-serif;display:block}.verso-viewer-root{height:100%;min-height:inherit}*{box-sizing:border-box}button,input{font:inherit}.verso-viewer-shell{background:#020617;border:1px solid #1e293b;flex-direction:column;height:100%;min-height:420px;display:flex}.verso-viewer-shell.graph-only{border:0}.verso-viewer-header{background:#0f172a;border-bottom:1px solid #1e293b;justify-content:space-between;align-items:center;gap:16px;min-height:52px;padding:9px 14px;display:flex}.verso-viewer-header strong,.verso-viewer-header span{display:block}.verso-viewer-header span{color:#64748b;margin-top:2px;font-size:11px}.verso-viewer-actions{align-items:center;gap:5px;margin-left:auto;display:flex}.verso-viewer-actions input{color:#e2e8f0;background:#020617;border:1px solid #334155;border-radius:4px;width:150px;padding:5px 7px}.verso-viewer-actions button{color:#bae6fd;cursor:pointer;background:#1e293b;border:1px solid #334155;border-radius:4px;padding:5px 8px}.verso-processing{color:#67e8f9;align-items:center;gap:8px;font-size:12px;display:flex}.verso-processing i{background:#22d3ee;border-radius:50%;width:8px;height:8px}.verso-processing.playing i{background:0 0;border:2px solid #164e63;border-top-color:#67e8f9;width:13px;height:13px;animation:.8s linear infinite verso-spin}@keyframes verso-spin{to{transform:rotate(360deg)}}.verso-viewer-main{flex:1;min-height:360px;display:flex;position:relative}.verso-viewer-canvas{flex:1;min-width:0;min-height:360px;position:relative}.verso-viewer-canvas>.react-flow{inset:0;width:100%!important;height:100%!important;position:absolute!important}.verso-graph-controls{z-index:8;opacity:0;pointer-events:none;flex-direction:column;gap:8px;transition:opacity .16s,transform .16s;display:flex;position:absolute;top:50%;left:14px;transform:translateY(-50%)translate(-5px)}.graph-only:hover .verso-graph-controls,.graph-only:focus-within .verso-graph-controls{opacity:1;pointer-events:auto;transform:translateY(-50%)translate(0)}.verso-graph-controls button{color:#cffafe;cursor:pointer;-webkit-backdrop-filter:blur(8px);backdrop-filter:blur(8px);background:#06111be0;border:1px solid #67e8f96b;border-radius:10px;flex-direction:column;justify-content:center;align-items:center;gap:2px;width:54px;min-height:52px;display:flex;box-shadow:0 8px 24px #00000052}.verso-graph-controls button:hover,.verso-graph-controls button:focus-visible{color:#fff;background:#0e7490c7;border-color:#67e8f9;outline:none}.verso-graph-controls button span{font-size:17px;line-height:1}.verso-graph-controls button small{letter-spacing:.06em;text-transform:uppercase;font-size:9px;font-weight:700}@media (hover:none){.verso-graph-controls{opacity:.82;pointer-events:auto;transform:translateY(-50%)}}.verso-viewer-inspector{background:#0f172a;border-left:1px solid #1e293b;width:260px;padding:14px}.verso-viewer-inspector button{float:right;color:#94a3b8;cursor:pointer;background:0 0;border:0}.verso-viewer-inspector h2{margin:0 20px 3px 0;font-size:16px}.verso-viewer-inspector p{color:#38bdf8;margin:0 0 14px;font-size:12px}.verso-viewer-inspector dt{color:#64748b;text-transform:uppercase;font-size:10px}.verso-viewer-inspector dd{margin:0 0 9px;font-size:12px}.verso-viewer-history{background:#0f172a;border-top:1px solid #1e293b;max-height:220px;overflow:hidden}.verso-playback-controls{border-bottom:1px solid #1e293b;align-items:center;gap:8px;padding:8px;display:flex}.verso-playback-controls button{color:#bae6fd;cursor:pointer;background:#1e293b;border:1px solid #334155;border-radius:4px;padding:3px 9px}.verso-playback-controls button:disabled{cursor:default;opacity:.35}.verso-playback-controls input{flex:1}.verso-playback-controls select{color:#bae6fd;background:#1e293b;border:1px solid #334155;border-radius:4px;padding:3px 5px}.verso-playback-controls span{color:#64748b;font-size:11px}.verso-viewer-history ol{max-height:155px;margin:0;padding:5px;list-style:none;overflow:auto}.verso-viewer-history li button{text-align:left;color:#cbd5e1;cursor:pointer;background:0 0;border:0;border-radius:3px;width:100%;padding:5px 8px}.verso-viewer-history li button:hover,.verso-viewer-history li button.active{color:#fff;background:#1e293b}.verso-viewer-history li span{color:#22d3ee;text-transform:uppercase;width:52px;font-size:9px;display:inline-block}:host([theme=light]) .verso-viewer-shell{color:#0f172a;background:#f8fafc;border-color:#cbd5e1}:host([theme=light]) .verso-viewer-header,:host([theme=light]) .verso-viewer-history,:host([theme=light]) .verso-viewer-inspector{background:#fff;border-color:#cbd5e1}.verso-viewer-message{color:#94a3b8;text-align:center;background:#020617;justify-content:center;align-items:center;min-height:420px;padding:24px;display:flex}.verso-viewer-message.error{color:#fca5a5}", Lf = class extends HTMLElement {
	static observedAttributes = [
		"src",
		"autoplay",
		"loop",
		"loop-delay",
		"controls",
		"chrome",
		"speed",
		"fit-padding",
		"max-zoom",
		"follow-zoom",
		"theme",
		"start-event"
	];
	root;
	value = null;
	loadGeneration = 0;
	documentRevision = 0;
	constructor() {
		super();
		let e = this.attachShadow({ mode: "open" }), t = document.createElement("style");
		t.textContent = `${g}\n${_}\n${If}`;
		let n = document.createElement("div");
		n.className = "verso-viewer-root", e.append(t, n), this.root = (0, h.createRoot)(n);
	}
	connectedCallback() {
		this.load();
	}
	attributeChangedCallback(e) {
		this.isConnected && (e === "src" ? this.load() : this.renderViewer());
	}
	set dag(e) {
		this.setValue(e);
	}
	set recording(e) {
		this.setValue(e);
	}
	setValue(e) {
		let t = Of(e);
		if (t) {
			this.renderMessage(t, !0), this.dispatchEvent(new CustomEvent("verso-viewer-error", { detail: { message: t } }));
			return;
		}
		this.value = e, this.documentRevision += 1, this.renderViewer(), this.dispatchEvent(new CustomEvent("verso-viewer-ready"));
	}
	async load() {
		let e = this.getAttribute("src");
		if (!e) {
			this.renderViewer();
			return;
		}
		let t = ++this.loadGeneration;
		this.renderMessage("Loading DAG…");
		try {
			let n = await fetch(e);
			if (!n.ok) throw Error(`Viewer source returned HTTP ${n.status}`);
			let r = await n.json();
			if (t !== this.loadGeneration) return;
			let i = Of(r);
			if (i) throw Error(i);
			this.value = r, this.documentRevision += 1, this.renderViewer(), this.dispatchEvent(new CustomEvent("verso-viewer-ready", { detail: { src: e } }));
		} catch (e) {
			let t = e instanceof Error ? e.message : String(e);
			this.renderMessage(t, !0), this.dispatchEvent(new CustomEvent("verso-viewer-error", { detail: { message: t } }));
		}
	}
	renderMessage(e, t = !1) {
		this.root.render(/* @__PURE__ */ (0, x.jsx)("div", {
			className: `verso-viewer-message ${t ? "error" : ""}`,
			role: t ? "alert" : "status",
			children: e
		}));
	}
	renderViewer() {
		this.value && this.root.render(/* @__PURE__ */ (0, x.jsx)(Pf, {
			document: this.value,
			autoplay: this.hasAttribute("autoplay"),
			loop: this.hasAttribute("loop"),
			loopDelayMs: Number(this.getAttribute("loop-delay") || 0),
			controls: !this.hasAttribute("controls") || this.getAttribute("controls") !== "false",
			chrome: !this.hasAttribute("chrome") || this.getAttribute("chrome") !== "false",
			speed: Number(this.getAttribute("speed") || 1),
			fitPadding: Number(this.getAttribute("fit-padding") || .25),
			maxZoom: Number(this.getAttribute("max-zoom") || 1),
			followZoom: Number(this.getAttribute("follow-zoom") || 1),
			startEvent: Number(this.getAttribute("start-event") || -1),
			onProgress: (e, t) => this.dispatchEvent(new CustomEvent("verso-replay-progress", { detail: {
				eventIndex: e,
				...t
			} })),
			onComplete: () => this.dispatchEvent(new CustomEvent("verso-replay-complete")),
			onChange: (e) => this.dispatchEvent(new CustomEvent("verso-viewer-change", { detail: e }))
		}, this.documentRevision));
	}
};
customElements.get("verso-dag-viewer") || customElements.define("verso-dag-viewer", Lf);
//#endregion
export { Lf as VersoDagViewerElement };
