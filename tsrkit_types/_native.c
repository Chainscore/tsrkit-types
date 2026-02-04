#include <Python.h>
#include <stdint.h>
#include <string.h>

static int
bit_length_ull(unsigned long long value) {
    int len = 0;
    while (value) {
        len++;
        value >>= 1;
    }
    return len;
}

static int
varint_size_ull(unsigned long long value) {
    if (value < (1ULL << 7)) {
        return 1;
    }
    if (value < (1ULL << 56)) {
        int bl = bit_length_ull(value);
        int l = (bl - 1) / 7;
        return 1 + l;
    }
    return 9;
}

static int
encode_varint_ull(unsigned long long value, unsigned char *out, Py_ssize_t out_len) {
    if (value < (1ULL << 7)) {
        if (out_len < 1) {
            return -1;
        }
        out[0] = (unsigned char)value;
        return 1;
    }
    if (value < (1ULL << 56)) {
        int bl = bit_length_ull(value);
        int l = (bl - 1) / 7;
        int size = 1 + l;
        if (out_len < size) {
            return -1;
        }
        unsigned char prefix_base = (unsigned char)(256 - (1 << (8 - l)));
        unsigned char high = (unsigned char)(value >> (8 * l));
        out[0] = (unsigned char)(prefix_base + high);
        unsigned long long remaining = value & ((1ULL << (8 * l)) - 1);
        for (int i = 0; i < l; i++) {
            out[1 + i] = (unsigned char)((remaining >> (8 * i)) & 0xFF);
        }
        return size;
    }
    if (out_len < 9) {
        return -1;
    }
    out[0] = 0xFF;
    for (int i = 0; i < 8; i++) {
        out[1 + i] = (unsigned char)((value >> (8 * i)) & 0xFF);
    }
    return 9;
}

static int
decode_varint_ull(const unsigned char *buf, Py_ssize_t buf_len, unsigned long long *value_out, Py_ssize_t *size_out) {
    if (buf_len <= 0) {
        return -1;
    }
    unsigned char tag = buf[0];
    if (tag < 0x80) {
        *value_out = (unsigned long long)tag;
        *size_out = 1;
        return 0;
    }
    if (tag == 0xFF) {
        if (buf_len < 9) {
            return -1;
        }
        unsigned long long value = 0;
        for (int i = 0; i < 8; i++) {
            value |= ((unsigned long long)buf[1 + i]) << (8 * i);
        }
        *value_out = value;
        *size_out = 9;
        return 0;
    }
    int l = 0;
    unsigned char t = tag;
    while (t & 0x80) {
        l++;
        t <<= 1;
    }
    if (buf_len < (Py_ssize_t)(l + 1)) {
        return -1;
    }
    unsigned long long alpha = (unsigned long long)tag + (1ULL << (8 - l)) - 256ULL;
    unsigned long long beta = 0;
    for (int i = 0; i < l; i++) {
        beta |= ((unsigned long long)buf[1 + i]) << (8 * i);
    }
    *value_out = (alpha << (l * 8)) | beta;
    *size_out = (Py_ssize_t)(l + 1);
    return 0;
}

static PyObject *
uint_encode(PyObject *self, PyObject *args) {
    PyObject *value_obj;
    int byte_size = 0;
    int is_signed = 0;
    if (!PyArg_ParseTuple(args, "Oip", &value_obj, &byte_size, &is_signed)) {
        return NULL;
    }

    if (byte_size > 0) {
        unsigned long long value = PyLong_AsUnsignedLongLong(value_obj);
        if (PyErr_Occurred()) {
            return NULL;
        }
        PyObject *out = PyBytes_FromStringAndSize(NULL, byte_size);
        if (!out) {
            return NULL;
        }
        unsigned char *buf = (unsigned char *)PyBytes_AS_STRING(out);
        for (int i = 0; i < byte_size; i++) {
            buf[i] = (unsigned char)((value >> (8 * i)) & 0xFF);
        }
        return out;
    }

    int bits = 64;
    unsigned long long value;
    if (is_signed) {
        long long signed_value = PyLong_AsLongLong(value_obj);
        if (PyErr_Occurred()) {
            return NULL;
        }
        unsigned long long bias = 1ULL << (bits - 1);
        value = (unsigned long long)(signed_value + (long long)bias);
    } else {
        value = PyLong_AsUnsignedLongLong(value_obj);
        if (PyErr_Occurred()) {
            return NULL;
        }
    }

    if (value < (1ULL << 7)) {
        unsigned char b = (unsigned char)value;
        return PyBytes_FromStringAndSize((char *)&b, 1);
    }

    if (value < (1ULL << 56)) {
        int bl = bit_length_ull(value);
        int l = (bl - 1) / 7;
        int size = 1 + l;
        PyObject *out = PyBytes_FromStringAndSize(NULL, size);
        if (!out) {
            return NULL;
        }
        unsigned char *buf = (unsigned char *)PyBytes_AS_STRING(out);
        unsigned char prefix_base = (unsigned char)(256 - (1 << (8 - l)));
        unsigned char high = (unsigned char)(value >> (8 * l));
        buf[0] = (unsigned char)(prefix_base + high);
        unsigned long long remaining = value & ((1ULL << (8 * l)) - 1);
        for (int i = 0; i < l; i++) {
            buf[1 + i] = (unsigned char)((remaining >> (8 * i)) & 0xFF);
        }
        return out;
    }

    PyObject *out = PyBytes_FromStringAndSize(NULL, 9);
    if (!out) {
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyBytes_AS_STRING(out);
    buf[0] = 0xFF;
    for (int i = 0; i < 8; i++) {
        buf[1 + i] = (unsigned char)((value >> (8 * i)) & 0xFF);
    }
    return out;
}

static PyObject *
uint_decode(PyObject *self, PyObject *args) {
    PyObject *obj;
    Py_ssize_t offset = 0;
    int byte_size = 0;
    int is_signed = 0;
    if (!PyArg_ParseTuple(args, "Onip", &obj, &offset, &byte_size, &is_signed)) {
        return NULL;
    }

    Py_buffer view;
    if (PyObject_GetBuffer(obj, &view, PyBUF_SIMPLE) != 0) {
        return NULL;
    }

    if (offset < 0 || offset >= view.len) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Offset out of range");
        return NULL;
    }

    const unsigned char *buf = (const unsigned char *)view.buf + offset;
    Py_ssize_t remaining = view.len - offset;

    if (byte_size > 0) {
        if (remaining < byte_size) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to decode integer");
            return NULL;
        }
        unsigned long long value = 0;
        for (int i = 0; i < byte_size; i++) {
            value |= ((unsigned long long)buf[i]) << (8 * i);
        }
        PyBuffer_Release(&view);
        return Py_BuildValue("Kn", value, (Py_ssize_t)byte_size);
    }

    unsigned char tag = buf[0];
    if (tag < 0x80) {
        PyBuffer_Release(&view);
        return Py_BuildValue("Kn", (unsigned long long)tag, (Py_ssize_t)1);
    }

    if (tag == 0xFF) {
        if (remaining < 9) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to decode 64-bit integer");
            return NULL;
        }
        unsigned long long value = 0;
        for (int i = 0; i < 8; i++) {
            value |= ((unsigned long long)buf[1 + i]) << (8 * i);
        }
        PyBuffer_Release(&view);
        return Py_BuildValue("Kn", value, (Py_ssize_t)9);
    }

    int l = 0;
    unsigned char t = tag;
    while (t & 0x80) {
        l++;
        t <<= 1;
    }
    if (remaining < (Py_ssize_t)(l + 1)) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to decode variable-length integer");
        return NULL;
    }
    unsigned long long alpha = (unsigned long long)tag + (1ULL << (8 - l)) - 256ULL;
    unsigned long long beta = 0;
    for (int i = 0; i < l; i++) {
        beta |= ((unsigned long long)buf[1 + i]) << (8 * i);
    }
    unsigned long long value = (alpha << (l * 8)) | beta;
    PyBuffer_Release(&view);
    return Py_BuildValue("Kn", value, (Py_ssize_t)(l + 1));
}

static PyObject *
pack_bits(PyObject *self, PyObject *args) {
    PyObject *seq_obj;
    Py_ssize_t bit_len = 0;
    const char *order;
    if (!PyArg_ParseTuple(args, "Ons", &seq_obj, &bit_len, &order)) {
        return NULL;
    }

    PyObject *seq = PySequence_Fast(seq_obj, "bits must be a sequence");
    if (!seq) {
        return NULL;
    }
    Py_ssize_t seq_len = PySequence_Fast_GET_SIZE(seq);
    PyObject **items = PySequence_Fast_ITEMS(seq);

    Py_ssize_t byte_count = (bit_len + 7) / 8;
    PyObject *out = PyBytes_FromStringAndSize(NULL, byte_count);
    if (!out) {
        Py_DECREF(seq);
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyBytes_AS_STRING(out);

    int msb = (order[0] == 'm');
    Py_ssize_t idx = 0;
    for (Py_ssize_t i = 0; i < byte_count; i++) {
        unsigned char val = 0;
        for (int j = 0; j < 8; j++) {
            int bit = 0;
            if (idx < bit_len && idx < seq_len) {
                bit = PyObject_IsTrue(items[idx]);
                if (bit < 0) {
                    Py_DECREF(seq);
                    Py_DECREF(out);
                    return NULL;
                }
            }
            if (bit) {
                val |= msb ? (1 << (7 - j)) : (1 << j);
            }
            idx++;
        }
        buf[i] = val;
    }

    Py_DECREF(seq);
    return out;
}

static PyObject *
unpack_bits(PyObject *self, PyObject *args) {
    PyObject *buf_obj;
    Py_ssize_t bit_len = 0;
    const char *order;
    if (!PyArg_ParseTuple(args, "Ons", &buf_obj, &bit_len, &order)) {
        return NULL;
    }

    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) != 0) {
        return NULL;
    }

    Py_ssize_t byte_count = (bit_len + 7) / 8;
    if (view.len < byte_count) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to decode bits");
        return NULL;
    }

    PyObject *list = PyList_New(bit_len);
    if (!list) {
        PyBuffer_Release(&view);
        return NULL;
    }

    int msb = (order[0] == 'm');
    const unsigned char *buf = (const unsigned char *)view.buf;
    for (Py_ssize_t i = 0; i < bit_len; i++) {
        Py_ssize_t byte_idx = i / 8;
        int bit_idx = (int)(i % 8);
        unsigned char byte = buf[byte_idx];
        int bit = msb ? ((byte >> (7 - bit_idx)) & 1) : ((byte >> bit_idx) & 1);
        PyObject *val = bit ? Py_True : Py_False;
        Py_INCREF(val);
        PyList_SET_ITEM(list, i, val);
    }

    PyBuffer_Release(&view);
    return list;
}

static PyObject *
bits_validate(PyObject *self, PyObject *args) {
    PyObject *seq_obj;
    if (!PyArg_ParseTuple(args, "O", &seq_obj)) {
        return NULL;
    }
    PyObject *seq = PySequence_Fast(seq_obj, "bits must be a sequence");
    if (!seq) {
        return NULL;
    }
    Py_ssize_t seq_len = PySequence_Fast_GET_SIZE(seq);
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < seq_len; i++) {
        if (!PyBool_Check(items[i])) {
            Py_DECREF(seq);
            PyErr_Format(PyExc_TypeError, "%R is not an instance of <class 'bool'>", items[i]);
            return NULL;
        }
    }
    Py_DECREF(seq);
    Py_RETURN_NONE;
}

static PyObject *
bits_validate_one(PyObject *self, PyObject *args) {
    PyObject *value;
    if (!PyArg_ParseTuple(args, "O", &value)) {
        return NULL;
    }
    if (!PyBool_Check(value)) {
        PyErr_Format(PyExc_TypeError, "%R is not an instance of <class 'bool'>", value);
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *
seq_validate(PyObject *self, PyObject *args) {
    PyObject *seq_obj;
    PyObject *type_obj;
    if (!PyArg_ParseTuple(args, "OO", &seq_obj, &type_obj)) {
        return NULL;
    }
    PyObject *seq = PySequence_Fast(seq_obj, "values must be a sequence");
    if (!seq) {
        return NULL;
    }
    Py_ssize_t seq_len = PySequence_Fast_GET_SIZE(seq);
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < seq_len; i++) {
        int ok = PyObject_IsInstance(items[i], type_obj);
        if (ok < 0) {
            Py_DECREF(seq);
            return NULL;
        }
        if (!ok) {
            Py_DECREF(seq);
            PyErr_Format(PyExc_TypeError, "%R is not an instance of %R", items[i], type_obj);
            return NULL;
        }
    }
    Py_DECREF(seq);
    Py_RETURN_NONE;
}

static PyObject *
seq_validate_one(PyObject *self, PyObject *args) {
    PyObject *value;
    PyObject *type_obj;
    if (!PyArg_ParseTuple(args, "OO", &value, &type_obj)) {
        return NULL;
    }
    int ok = PyObject_IsInstance(value, type_obj);
    if (ok < 0) {
        return NULL;
    }
    if (!ok) {
        PyErr_Format(PyExc_TypeError, "%R is not an instance of %R", value, type_obj);
        return NULL;
    }
    Py_RETURN_NONE;
}

static PyObject *
encode_fixed_array(PyObject *self, PyObject *args) {
    PyObject *seq_obj;
    int byte_size = 0;
    if (!PyArg_ParseTuple(args, "Oi", &seq_obj, &byte_size)) {
        return NULL;
    }

    PyObject *seq = PySequence_Fast(seq_obj, "values must be a sequence");
    if (!seq) {
        return NULL;
    }
    Py_ssize_t count = PySequence_Fast_GET_SIZE(seq);
    PyObject **items = PySequence_Fast_ITEMS(seq);

    Py_ssize_t total = count * byte_size;
    PyObject *out = PyBytes_FromStringAndSize(NULL, total);
    if (!out) {
        Py_DECREF(seq);
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyBytes_AS_STRING(out);

    for (Py_ssize_t i = 0; i < count; i++) {
        unsigned long long value = PyLong_AsUnsignedLongLong(items[i]);
        if (PyErr_Occurred()) {
            Py_DECREF(seq);
            Py_DECREF(out);
            return NULL;
        }
        for (int b = 0; b < byte_size; b++) {
            buf[i * byte_size + b] = (unsigned char)((value >> (8 * b)) & 0xFF);
        }
    }

    Py_DECREF(seq);
    return out;
}

static PyObject *
decode_fixed_array(PyObject *self, PyObject *args) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    Py_ssize_t count = 0;
    int byte_size = 0;
    PyObject *type_obj;
    if (!PyArg_ParseTuple(args, "OnniO", &buf_obj, &offset, &count, &byte_size, &type_obj)) {
        return NULL;
    }

    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) != 0) {
        return NULL;
    }

    Py_ssize_t total = count * byte_size;
    if (offset < 0 || offset + total > view.len) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to decode fixed array");
        return NULL;
    }

    const unsigned char *buf = (const unsigned char *)view.buf + offset;
    PyObject *list = PyList_New(count);
    if (!list) {
        PyBuffer_Release(&view);
        return NULL;
    }

    for (Py_ssize_t i = 0; i < count; i++) {
        unsigned long long value = 0;
        for (int b = 0; b < byte_size; b++) {
            value |= ((unsigned long long)buf[i * byte_size + b]) << (8 * b);
        }
        PyObject *val_obj = PyLong_FromUnsignedLongLong(value);
        if (!val_obj) {
            PyBuffer_Release(&view);
            Py_DECREF(list);
            return NULL;
        }
        PyObject *typed = PyObject_CallFunctionObjArgs(type_obj, val_obj, NULL);
        Py_DECREF(val_obj);
        if (!typed) {
            PyBuffer_Release(&view);
            Py_DECREF(list);
            return NULL;
        }
        PyList_SET_ITEM(list, i, typed);
    }

    PyBuffer_Release(&view);
    return Py_BuildValue("Nn", list, total);
}

static int
get_class_ssize_attr(PyObject *type, const char *name, Py_ssize_t *out, Py_ssize_t default_val) {
    PyObject *val = PyObject_GetAttrString(type, name);
    if (!val) {
        PyErr_Clear();
        *out = default_val;
        return 0;
    }
    if (!PyLong_Check(val)) {
        Py_DECREF(val);
        PyErr_Format(PyExc_TypeError, "%s must be int", name);
        return -1;
    }
    *out = PyLong_AsSsize_t(val);
    Py_DECREF(val);
    if (PyErr_Occurred()) {
        if (PyErr_ExceptionMatches(PyExc_OverflowError)) {
            PyErr_Clear();
            *out = PY_SSIZE_T_MAX;
            return 0;
        }
        return -1;
    }
    return 0;
}

static int
get_class_order_msb(PyObject *type, int *is_msb) {
    PyObject *val = PyObject_GetAttrString(type, "_order");
    if (!val) {
        PyErr_Clear();
        *is_msb = 1;
        return 0;
    }
    if (!PyUnicode_Check(val)) {
        Py_DECREF(val);
        PyErr_SetString(PyExc_TypeError, "_order must be str");
        return -1;
    }
    int ch = (int)PyUnicode_ReadChar(val, 0);
    Py_DECREF(val);
    if (ch < 0) {
        return -1;
    }
    *is_msb = (ch == 'm');
    return 0;
}

static int
get_class_optional_length(PyObject *type, Py_ssize_t *length, int *is_fixed) {
    PyObject *val = PyObject_GetAttrString(type, "_length");
    if (!val) {
        PyErr_Clear();
        *length = 0;
        *is_fixed = 0;
        return 0;
    }
    if (val == Py_None) {
        Py_DECREF(val);
        *length = 0;
        *is_fixed = 0;
        return 0;
    }
    if (!PyLong_Check(val)) {
        Py_DECREF(val);
        PyErr_SetString(PyExc_TypeError, "_length must be int or None");
        return -1;
    }
    *length = PyLong_AsSsize_t(val);
    Py_DECREF(val);
    if (PyErr_Occurred()) {
        return -1;
    }
    *is_fixed = 1;
    return 0;
}

static int
call_encode_size(PyObject *obj, Py_ssize_t *out) {
    PyObject *res = PyObject_CallMethod(obj, "encode_size", NULL);
    if (!res) {
        return -1;
    }
    Py_ssize_t size = PyLong_AsSsize_t(res);
    Py_DECREF(res);
    if (PyErr_Occurred()) {
        return -1;
    }
    *out = size;
    return 0;
}

static int
call_encode_into(PyObject *obj, PyObject *buffer, Py_ssize_t offset, Py_ssize_t *written) {
    PyObject *res = PyObject_CallMethod(obj, "encode_into", "On", buffer, offset);
    if (!res) {
        return -1;
    }
    Py_ssize_t size = PyLong_AsSsize_t(res);
    Py_DECREF(res);
    if (PyErr_Occurred()) {
        return -1;
    }
    *written = size;
    return 0;
}

static int
call_decode_from(PyObject *type, PyObject *buffer, Py_ssize_t offset, PyObject **value_out, Py_ssize_t *size_out) {
    PyObject *res = PyObject_CallMethod(type, "decode_from", "On", buffer, offset);
    if (!res) {
        return -1;
    }
    if (!PyTuple_Check(res) || PyTuple_GET_SIZE(res) < 2) {
        Py_DECREF(res);
        PyErr_SetString(PyExc_ValueError, "Invalid decode_from result");
        return -1;
    }
    PyObject *value = PyTuple_GET_ITEM(res, 0);
    PyObject *size_obj = PyTuple_GET_ITEM(res, 1);
    Py_INCREF(value);
    Py_ssize_t size = PyLong_AsSsize_t(size_obj);
    Py_DECREF(res);
    if (PyErr_Occurred()) {
        Py_DECREF(value);
        return -1;
    }
    *value_out = value;
    *size_out = size;
    return 0;
}

/* ------------------------------ NativeBits ------------------------------ */

typedef struct {
    PyObject_HEAD
    Py_ssize_t bit_len;
    Py_ssize_t cap_bits;
    unsigned char *data; /* lsb-packed */
} NativeBits;

static PyObject *nativebits_as_list(NativeBits *bits);
static int nativebits_rebuild_from_sequence(NativeBits *bits, PyObject *seq_obj);

static int
nativebits_ensure_capacity(NativeBits *self, Py_ssize_t bits_needed) {
    if (bits_needed <= self->cap_bits) {
        return 0;
    }
    Py_ssize_t new_cap = self->cap_bits ? self->cap_bits : 8;
    while (new_cap < bits_needed) {
        new_cap *= 2;
    }
    Py_ssize_t new_bytes = (new_cap + 7) / 8;
    Py_ssize_t old_bytes = (self->cap_bits + 7) / 8;
    unsigned char *new_data = (unsigned char *)PyMem_Realloc(self->data, new_bytes);
    if (!new_data) {
        PyErr_NoMemory();
        return -1;
    }
    if (new_bytes > old_bytes) {
        memset(new_data + old_bytes, 0, (size_t)(new_bytes - old_bytes));
    }
    self->data = new_data;
    self->cap_bits = new_cap;
    return 0;
}

static inline int
nativebits_get(const NativeBits *self, Py_ssize_t idx) {
    Py_ssize_t byte_idx = idx / 8;
    int bit_idx = (int)(idx % 8);
    return (self->data[byte_idx] >> bit_idx) & 1;
}

static inline void
nativebits_set(NativeBits *self, Py_ssize_t idx, int value) {
    Py_ssize_t byte_idx = idx / 8;
    int bit_idx = (int)(idx % 8);
    unsigned char mask = (unsigned char)(1 << bit_idx);
    if (value) {
        self->data[byte_idx] |= mask;
    } else {
        self->data[byte_idx] &= (unsigned char)(~mask);
    }
}

static int
nativebits_check_length(NativeBits *self, Py_ssize_t new_len) {
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    PyObject *type = (PyObject *)Py_TYPE(self);
    if (get_class_ssize_attr(type, "_min_length", &min_len, 0) < 0) {
        return -1;
    }
    if (get_class_ssize_attr(type, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        return -1;
    }
    if (new_len < min_len) {
        PyErr_Format(PyExc_ValueError, "Vector: Expected sequence size to be >= %zd, resultant size %zd", min_len, new_len);
        return -1;
    }
    if (new_len > max_len) {
        PyErr_Format(PyExc_ValueError, "Vector: Expected sequence size to be <= %zd, resultant size %zd", max_len, new_len);
        return -1;
    }
    return 0;
}

static void
NativeBits_dealloc(NativeBits *self) {
    PyMem_Free(self->data);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
NativeBits_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    NativeBits *self = (NativeBits *)type->tp_alloc(type, 0);
    if (!self) {
        return NULL;
    }
    self->bit_len = 0;
    self->cap_bits = 0;
    self->data = NULL;
    return (PyObject *)self;
}

static int
NativeBits_init(NativeBits *self, PyObject *args, PyObject *kwds) {
    PyObject *seq_obj = NULL;
    if (!PyArg_ParseTuple(args, "|O", &seq_obj)) {
        return -1;
    }
    if (!seq_obj) {
        if (nativebits_check_length(self, 0) < 0) {
            return -1;
        }
        return 0;
    }
    PyObject *seq = PySequence_Fast(seq_obj, "bits must be a sequence");
    if (!seq) {
        return -1;
    }
    Py_ssize_t seq_len = PySequence_Fast_GET_SIZE(seq);
    if (nativebits_ensure_capacity(self, seq_len) < 0) {
        Py_DECREF(seq);
        return -1;
    }
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < seq_len; i++) {
        if (!PyBool_Check(items[i])) {
            Py_DECREF(seq);
            PyErr_Format(PyExc_TypeError, "%R is not an instance of <class 'bool'>", items[i]);
            return -1;
        }
        nativebits_set(self, i, items[i] == Py_True);
    }
    self->bit_len = seq_len;
    Py_DECREF(seq);
    if (nativebits_check_length(self, self->bit_len) < 0) {
        return -1;
    }
    return 0;
}

static Py_ssize_t
NativeBits_len(PyObject *self) {
    return ((NativeBits *)self)->bit_len;
}

static PyObject *
NativeBits_item(PyObject *self, Py_ssize_t idx) {
    NativeBits *bits = (NativeBits *)self;
    if (idx < 0) {
        idx += bits->bit_len;
    }
    if (idx < 0 || idx >= bits->bit_len) {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return NULL;
    }
    if (nativebits_get(bits, idx)) {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

static int
NativeBits_ass_item(PyObject *self, Py_ssize_t idx, PyObject *value) {
    NativeBits *bits = (NativeBits *)self;
    if (idx < 0) {
        idx += bits->bit_len;
    }
    if (idx < 0 || idx >= bits->bit_len) {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return -1;
    }
    if (!PyBool_Check(value)) {
        PyErr_Format(PyExc_TypeError, "%R is not an instance of <class 'bool'>", value);
        return -1;
    }
    nativebits_set(bits, idx, value == Py_True);
    return 0;
}

static PyObject *
NativeBits_subscript(PyObject *self, PyObject *item) {
    NativeBits *bits = (NativeBits *)self;
    if (PyIndex_Check(item)) {
        Py_ssize_t idx = PyNumber_AsSsize_t(item, PyExc_IndexError);
        if (idx == -1 && PyErr_Occurred()) {
            return NULL;
        }
        return NativeBits_item(self, idx);
    }
    if (PySlice_Check(item)) {
        Py_ssize_t start, stop, step, slicelen;
        if (PySlice_GetIndicesEx(item, bits->bit_len, &start, &stop, &step, &slicelen) < 0) {
            return NULL;
        }
        PyObject *list = PyList_New(slicelen);
        if (!list) {
            return NULL;
        }
        for (Py_ssize_t i = 0; i < slicelen; i++) {
            Py_ssize_t idx = start + i * step;
            PyObject *val = nativebits_get(bits, idx) ? Py_True : Py_False;
            Py_INCREF(val);
            PyList_SET_ITEM(list, i, val);
        }
        return list;
    }
    PyErr_SetString(PyExc_TypeError, "indices must be int or slice");
    return NULL;
}

static int
NativeBits_ass_subscript(PyObject *self, PyObject *item, PyObject *value) {
    if (PyIndex_Check(item)) {
        Py_ssize_t idx = PyNumber_AsSsize_t(item, PyExc_IndexError);
        if (idx == -1 && PyErr_Occurred()) {
            return -1;
        }
        return NativeBits_ass_item(self, idx, value);
    }
    if (PySlice_Check(item)) {
        NativeBits *bits = (NativeBits *)self;
        PyObject *list = nativebits_as_list(bits);
        if (!list) {
            return -1;
        }
        if (PyObject_SetItem(list, item, value) < 0) {
            Py_DECREF(list);
            return -1;
        }
        int rc = nativebits_rebuild_from_sequence(bits, list);
        Py_DECREF(list);
        return rc;
    }
    PyErr_SetString(PyExc_TypeError, "indices must be int or slice");
    return -1;
}

static PyObject *
NativeBits_append(PyObject *self, PyObject *args) {
    NativeBits *bits = (NativeBits *)self;
    PyObject *value;
    if (!PyArg_ParseTuple(args, "O", &value)) {
        return NULL;
    }
    if (!PyBool_Check(value)) {
        PyErr_Format(PyExc_TypeError, "%R is not an instance of <class 'bool'>", value);
        return NULL;
    }
    Py_ssize_t new_len = bits->bit_len + 1;
    if (nativebits_check_length(bits, new_len) < 0) {
        return NULL;
    }
    if (nativebits_ensure_capacity(bits, new_len) < 0) {
        return NULL;
    }
    nativebits_set(bits, bits->bit_len, value == Py_True);
    bits->bit_len = new_len;
    Py_RETURN_NONE;
}

static PyObject *
NativeBits_extend(PyObject *self, PyObject *args) {
    NativeBits *bits = (NativeBits *)self;
    PyObject *seq_obj;
    if (!PyArg_ParseTuple(args, "O", &seq_obj)) {
        return NULL;
    }
    PyObject *seq = PySequence_Fast(seq_obj, "bits must be a sequence");
    if (!seq) {
        return NULL;
    }
    Py_ssize_t seq_len = PySequence_Fast_GET_SIZE(seq);
    Py_ssize_t new_len = bits->bit_len + seq_len;
    if (nativebits_check_length(bits, new_len) < 0) {
        Py_DECREF(seq);
        return NULL;
    }
    if (nativebits_ensure_capacity(bits, new_len) < 0) {
        Py_DECREF(seq);
        return NULL;
    }
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < seq_len; i++) {
        if (!PyBool_Check(items[i])) {
            Py_DECREF(seq);
            PyErr_Format(PyExc_TypeError, "%R is not an instance of <class 'bool'>", items[i]);
            return NULL;
        }
        nativebits_set(bits, bits->bit_len + i, items[i] == Py_True);
    }
    bits->bit_len = new_len;
    Py_DECREF(seq);
    Py_RETURN_NONE;
}

static PyObject *
NativeBits_insert(PyObject *self, PyObject *args) {
    NativeBits *bits = (NativeBits *)self;
    Py_ssize_t idx;
    PyObject *value;
    if (!PyArg_ParseTuple(args, "nO", &idx, &value)) {
        return NULL;
    }
    if (!PyBool_Check(value)) {
        PyErr_Format(PyExc_TypeError, "%R is not an instance of <class 'bool'>", value);
        return NULL;
    }
    if (idx < 0) {
        idx += bits->bit_len;
    }
    if (idx < 0) {
        idx = 0;
    }
    if (idx > bits->bit_len) {
        idx = bits->bit_len;
    }
    Py_ssize_t new_len = bits->bit_len + 1;
    if (nativebits_check_length(bits, new_len) < 0) {
        return NULL;
    }
    if (nativebits_ensure_capacity(bits, new_len) < 0) {
        return NULL;
    }
    for (Py_ssize_t i = bits->bit_len; i > idx; i--) {
        nativebits_set(bits, i, nativebits_get(bits, i - 1));
    }
    nativebits_set(bits, idx, value == Py_True);
    bits->bit_len = new_len;
    Py_RETURN_NONE;
}

static PyObject *
NativeBits_pop(PyObject *self, PyObject *args) {
    NativeBits *bits = (NativeBits *)self;
    Py_ssize_t idx = -1;
    if (!PyArg_ParseTuple(args, "|n", &idx)) {
        return NULL;
    }
    if (bits->bit_len == 0) {
        PyErr_SetString(PyExc_IndexError, "pop from empty Bits");
        return NULL;
    }
    if (idx < 0) {
        idx += bits->bit_len;
    }
    if (idx < 0 || idx >= bits->bit_len) {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return NULL;
    }
    int bit = nativebits_get(bits, idx);
    for (Py_ssize_t i = idx; i < bits->bit_len - 1; i++) {
        nativebits_set(bits, i, nativebits_get(bits, i + 1));
    }
    bits->bit_len -= 1;
    if (nativebits_check_length(bits, bits->bit_len) < 0) {
        return NULL;
    }
    if (bit) {
        Py_RETURN_TRUE;
    }
    Py_RETURN_FALSE;
}

static PyObject *
nativebits_as_list(NativeBits *bits) {
    PyObject *list = PyList_New(bits->bit_len);
    if (!list) {
        return NULL;
    }
    for (Py_ssize_t i = 0; i < bits->bit_len; i++) {
        PyObject *val = nativebits_get(bits, i) ? Py_True : Py_False;
        Py_INCREF(val);
        PyList_SET_ITEM(list, i, val);
    }
    return list;
}

static int
nativebits_rebuild_from_sequence(NativeBits *bits, PyObject *seq_obj) {
    PyObject *seq = PySequence_Fast(seq_obj, "bits must be a sequence");
    if (!seq) {
        return -1;
    }
    Py_ssize_t seq_len = PySequence_Fast_GET_SIZE(seq);
    if (nativebits_ensure_capacity(bits, seq_len) < 0) {
        Py_DECREF(seq);
        return -1;
    }
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < seq_len; i++) {
        if (!PyBool_Check(items[i])) {
            Py_DECREF(seq);
            PyErr_Format(PyExc_TypeError, "%R is not an instance of <class 'bool'>", items[i]);
            return -1;
        }
        nativebits_set(bits, i, items[i] == Py_True);
    }
    bits->bit_len = seq_len;
    Py_DECREF(seq);
    if (nativebits_check_length(bits, bits->bit_len) < 0) {
        return -1;
    }
    return 0;
}

static int
nativebits_compare(NativeBits *bits, PyObject *other) {
    if (!PySequence_Check(other)) {
        return -2;
    }
    PyObject *seq = PySequence_Fast(other, "comparison requires a sequence");
    if (!seq) {
        return -1;
    }
    Py_ssize_t other_len = PySequence_Fast_GET_SIZE(seq);
    if (other_len != bits->bit_len) {
        Py_DECREF(seq);
        return 0;
    }
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < bits->bit_len; i++) {
        PyObject *val = nativebits_get(bits, i) ? Py_True : Py_False;
        int eq = PyObject_RichCompareBool(items[i], val, Py_EQ);
        if (eq < 0) {
            Py_DECREF(seq);
            return -1;
        }
        if (!eq) {
            Py_DECREF(seq);
            return 0;
        }
    }
    Py_DECREF(seq);
    return 1;
}

static PyObject *
NativeBits_richcompare(PyObject *self, PyObject *other, int op) {
    if (op != Py_EQ && op != Py_NE) {
        Py_RETURN_NOTIMPLEMENTED;
    }
    int eq = nativebits_compare((NativeBits *)self, other);
    if (eq == -2) {
        Py_RETURN_NOTIMPLEMENTED;
    }
    if (eq < 0) {
        return NULL;
    }
    if (op == Py_NE) {
        eq = !eq;
    }
    return PyBool_FromLong(eq);
}

static PyObject *
NativeBits_repr(PyObject *self) {
    NativeBits *bits = (NativeBits *)self;
    PyObject *list = nativebits_as_list(bits);
    if (!list) {
        return NULL;
    }
    PyObject *list_repr = PyObject_Repr(list);
    Py_DECREF(list);
    if (!list_repr) {
        return NULL;
    }
    PyObject *name = PyObject_GetAttrString((PyObject *)Py_TYPE(self), "__name__");
    if (!name) {
        Py_DECREF(list_repr);
        return NULL;
    }
    PyObject *result = PyUnicode_FromFormat("%S(%S)", name, list_repr);
    Py_DECREF(name);
    Py_DECREF(list_repr);
    return result;
}

static PyObject *
NativeBits_encode_size(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    NativeBits *bits = (NativeBits *)self;
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    PyObject *type = (PyObject *)Py_TYPE(self);
    if (get_class_ssize_attr(type, "_min_length", &min_len, 0) < 0) {
        return NULL;
    }
    if (get_class_ssize_attr(type, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        return NULL;
    }
    Py_ssize_t byte_count = (bits->bit_len + 7) / 8;
    if (min_len == max_len && min_len > 0) {
        return PyLong_FromSsize_t(byte_count);
    }
    int prefix = varint_size_ull((unsigned long long)bits->bit_len);
    if (prefix < 0) {
        PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
        return NULL;
    }
    return PyLong_FromSsize_t((Py_ssize_t)prefix + byte_count);
}

static PyObject *
NativeBits_encode(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    NativeBits *bits = (NativeBits *)self;
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    PyObject *type = (PyObject *)Py_TYPE(self);
    if (get_class_ssize_attr(type, "_min_length", &min_len, 0) < 0) {
        return NULL;
    }
    if (get_class_ssize_attr(type, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        return NULL;
    }
    if (min_len == max_len && min_len > 0 && bits->bit_len != min_len) {
        PyErr_Format(PyExc_ValueError, "Bit sequence length mismatch: expected %zd, got %zd", min_len, bits->bit_len);
        return NULL;
    }
    int is_msb = 1;
    if (get_class_order_msb(type, &is_msb) < 0) {
        return NULL;
    }
    Py_ssize_t byte_count = (bits->bit_len + 7) / 8;
    int prefix = 0;
    if (!(min_len == max_len && min_len > 0)) {
        prefix = varint_size_ull((unsigned long long)bits->bit_len);
        if (prefix < 0) {
            PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
            return NULL;
        }
    }
    PyObject *out = PyBytes_FromStringAndSize(NULL, prefix + byte_count);
    if (!out) {
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyBytes_AS_STRING(out);
    Py_ssize_t offset = 0;
    if (prefix > 0) {
        int wrote = encode_varint_ull((unsigned long long)bits->bit_len, buf, prefix);
        if (wrote < 0) {
            Py_DECREF(out);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to encode length");
            return NULL;
        }
        offset = wrote;
    }
    memset(buf + offset, 0, (size_t)byte_count);
    for (Py_ssize_t i = 0; i < bits->bit_len; i++) {
        if (nativebits_get(bits, i)) {
            Py_ssize_t byte_idx = i / 8;
            int bit_idx = (int)(i % 8);
            if (is_msb) {
                buf[offset + byte_idx] |= (unsigned char)(1 << (7 - bit_idx));
            } else {
                buf[offset + byte_idx] |= (unsigned char)(1 << bit_idx);
            }
        }
    }
    return out;
}

static PyObject *
NativeBits_encode_into(PyObject *self, PyObject *args, PyObject *kwargs) {
    NativeBits *bits = (NativeBits *)self;
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    static char *kwlist[] = {"buffer", "offset", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|n", kwlist, &buf_obj, &offset)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_WRITABLE) != 0) {
        return NULL;
    }
    PyObject *type = (PyObject *)Py_TYPE(self);
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    if (get_class_ssize_attr(type, "_min_length", &min_len, 0) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    if (get_class_ssize_attr(type, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    if (min_len == max_len && min_len > 0 && bits->bit_len != min_len) {
        PyBuffer_Release(&view);
        PyErr_Format(PyExc_ValueError, "Bit sequence length mismatch: expected %zd, got %zd", min_len, bits->bit_len);
        return NULL;
    }
    int is_msb = 1;
    if (get_class_order_msb(type, &is_msb) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    Py_ssize_t byte_count = (bits->bit_len + 7) / 8;
    int prefix = 0;
    if (!(min_len == max_len && min_len > 0)) {
        prefix = varint_size_ull((unsigned long long)bits->bit_len);
        if (prefix < 0) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
            return NULL;
        }
    }
    Py_ssize_t total = prefix + byte_count;
    if (offset < 0 || offset + total > view.len) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to encode value");
        return NULL;
    }
    unsigned char *buf = (unsigned char *)view.buf + offset;
    if (prefix > 0) {
        int wrote = encode_varint_ull((unsigned long long)bits->bit_len, buf, prefix);
        if (wrote < 0) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to encode length");
            return NULL;
        }
        buf += wrote;
    }
    memset(buf, 0, (size_t)byte_count);
    for (Py_ssize_t i = 0; i < bits->bit_len; i++) {
        if (nativebits_get(bits, i)) {
            Py_ssize_t byte_idx = i / 8;
            int bit_idx = (int)(i % 8);
            if (is_msb) {
                buf[byte_idx] |= (unsigned char)(1 << (7 - bit_idx));
            } else {
                buf[byte_idx] |= (unsigned char)(1 << bit_idx);
            }
        }
    }
    PyBuffer_Release(&view);
    return PyLong_FromSsize_t(total);
}

static PyObject *
NativeBits_decode_from(PyObject *cls, PyObject *args) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    if (!PyArg_ParseTuple(args, "O|n", &buf_obj, &offset)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) != 0) {
        return NULL;
    }
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    if (get_class_ssize_attr(cls, "_min_length", &min_len, 0) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    if (get_class_ssize_attr(cls, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    int is_msb = 1;
    if (get_class_order_msb(cls, &is_msb) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    const unsigned char *buf = (const unsigned char *)view.buf + offset;
    Py_ssize_t remaining = view.len - offset;
    unsigned long long bit_len = 0;
    Py_ssize_t prefix = 0;
    if (min_len == max_len && min_len > 0) {
        bit_len = (unsigned long long)min_len;
    } else {
        if (decode_varint_ull(buf, remaining, &bit_len, &prefix) < 0) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to decode length");
            return NULL;
        }
        buf += prefix;
        remaining -= prefix;
    }
    if (bit_len > (unsigned long long)PY_SSIZE_T_MAX) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Bit sequence too large to decode");
        return NULL;
    }
    if (bit_len < (unsigned long long)min_len || bit_len > (unsigned long long)max_len) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Bit sequence length out of bounds");
        return NULL;
    }
    Py_ssize_t byte_count = (Py_ssize_t)((bit_len + 7) / 8);
    if (remaining < byte_count) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to decode bits");
        return NULL;
    }
    NativeBits *self = (NativeBits *)NativeBits_new((PyTypeObject *)cls, NULL, NULL);
    if (!self) {
        PyBuffer_Release(&view);
        return NULL;
    }
    if (nativebits_ensure_capacity(self, (Py_ssize_t)bit_len) < 0) {
        PyBuffer_Release(&view);
        Py_DECREF(self);
        return NULL;
    }
    self->bit_len = (Py_ssize_t)bit_len;
    memset(self->data, 0, (size_t)((self->cap_bits + 7) / 8));
    for (Py_ssize_t i = 0; i < self->bit_len; i++) {
        Py_ssize_t byte_idx = i / 8;
        int bit_idx = (int)(i % 8);
        unsigned char byte = buf[byte_idx];
        int bit = is_msb ? ((byte >> (7 - bit_idx)) & 1) : ((byte >> bit_idx) & 1);
        nativebits_set(self, i, bit);
    }
    PyBuffer_Release(&view);
    return Py_BuildValue("Nn", (PyObject *)self, prefix + byte_count);
}

static PyObject *
NativeBits_decode(PyObject *cls, PyObject *args) {
    PyObject *tuple = NativeBits_decode_from(cls, args);
    if (!tuple) {
        return NULL;
    }
    if (!PyTuple_Check(tuple) || PyTuple_GET_SIZE(tuple) < 1) {
        Py_DECREF(tuple);
        PyErr_SetString(PyExc_ValueError, "Invalid decode_from result");
        return NULL;
    }
    PyObject *bits = PyTuple_GET_ITEM(tuple, 0);
    Py_INCREF(bits);
    Py_DECREF(tuple);
    return bits;
}

static PyObject *
NativeBits_to_json(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    NativeBits *bits = (NativeBits *)self;
    int is_msb = 1;
    if (get_class_order_msb((PyObject *)Py_TYPE(self), &is_msb) < 0) {
        return NULL;
    }
    Py_ssize_t byte_count = (bits->bit_len + 7) / 8;
    PyObject *bytes_obj = PyBytes_FromStringAndSize(NULL, byte_count);
    if (!bytes_obj) {
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyBytes_AS_STRING(bytes_obj);
    memset(buf, 0, (size_t)byte_count);
    for (Py_ssize_t i = 0; i < bits->bit_len; i++) {
        if (nativebits_get(bits, i)) {
            Py_ssize_t byte_idx = i / 8;
            int bit_idx = (int)(i % 8);
            if (is_msb) {
                buf[byte_idx] |= (unsigned char)(1 << (7 - bit_idx));
            } else {
                buf[byte_idx] |= (unsigned char)(1 << bit_idx);
            }
        }
    }
    PyObject *hex = PyObject_CallMethod(bytes_obj, "hex", NULL);
    Py_DECREF(bytes_obj);
    return hex;
}

static PyObject *
NativeBits_from_json(PyObject *cls, PyObject *args) {
    PyObject *str_obj;
    if (!PyArg_ParseTuple(args, "O", &str_obj)) {
        return NULL;
    }
    PyObject *clean = PyObject_CallMethod(str_obj, "replace", "ss", "0x", "");
    if (!clean) {
        return NULL;
    }
    PyObject *bytes_type = (PyObject *)&PyBytes_Type;
    PyObject *bytes_obj = PyObject_CallMethod(bytes_type, "fromhex", "O", clean);
    Py_DECREF(clean);
    if (!bytes_obj) {
        return NULL;
    }
    Py_ssize_t byte_len = PyBytes_GET_SIZE(bytes_obj);
    const unsigned char *buf = (const unsigned char *)PyBytes_AS_STRING(bytes_obj);
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    if (get_class_ssize_attr(cls, "_min_length", &min_len, 0) < 0) {
        Py_DECREF(bytes_obj);
        return NULL;
    }
    if (get_class_ssize_attr(cls, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        Py_DECREF(bytes_obj);
        return NULL;
    }
    int is_msb = 1;
    if (get_class_order_msb(cls, &is_msb) < 0) {
        Py_DECREF(bytes_obj);
        return NULL;
    }
    Py_ssize_t bit_len = byte_len * 8;
    if (min_len == max_len && min_len > 0 && min_len < bit_len) {
        bit_len = min_len;
    }
    NativeBits *self = (NativeBits *)NativeBits_new((PyTypeObject *)cls, NULL, NULL);
    if (!self) {
        Py_DECREF(bytes_obj);
        return NULL;
    }
    if (nativebits_ensure_capacity(self, bit_len) < 0) {
        Py_DECREF(bytes_obj);
        Py_DECREF(self);
        return NULL;
    }
    self->bit_len = bit_len;
    memset(self->data, 0, (size_t)((self->cap_bits + 7) / 8));
    for (Py_ssize_t i = 0; i < bit_len; i++) {
        Py_ssize_t byte_idx = i / 8;
        int bit_idx = (int)(i % 8);
        unsigned char byte = buf[byte_idx];
        int bit = is_msb ? ((byte >> (7 - bit_idx)) & 1) : ((byte >> bit_idx) & 1);
        nativebits_set(self, i, bit);
    }
    Py_DECREF(bytes_obj);
    if (nativebits_check_length(self, self->bit_len) < 0) {
        Py_DECREF(self);
        return NULL;
    }
    return (PyObject *)self;
}

static PyMethodDef NativeBits_methods[] = {
    {"append", NativeBits_append, METH_VARARGS, "Append a bit."},
    {"extend", NativeBits_extend, METH_VARARGS, "Extend with a sequence of bits."},
    {"insert", NativeBits_insert, METH_VARARGS, "Insert a bit."},
    {"pop", NativeBits_pop, METH_VARARGS, "Pop a bit."},
    {"encode_size", NativeBits_encode_size, METH_NOARGS, "Encoded size."},
    {"encode", NativeBits_encode, METH_NOARGS, "Encode to bytes."},
    {"encode_into", (PyCFunction)NativeBits_encode_into, METH_VARARGS | METH_KEYWORDS, "Encode into buffer."},
    {"decode_from", NativeBits_decode_from, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {"decode", NativeBits_decode, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {"to_json", NativeBits_to_json, METH_NOARGS, "Convert to JSON."},
    {"from_json", NativeBits_from_json, METH_CLASS | METH_VARARGS, "Create from JSON."},
    {NULL, NULL, 0, NULL},
};

static PySequenceMethods NativeBits_as_sequence = {
    .sq_length = NativeBits_len,
    .sq_item = (ssizeargfunc)NativeBits_item,
    .sq_ass_item = (ssizeobjargproc)NativeBits_ass_item,
};

static PyMappingMethods NativeBits_as_mapping = {
    .mp_length = NativeBits_len,
    .mp_subscript = NativeBits_subscript,
    .mp_ass_subscript = NativeBits_ass_subscript,
};

static PyTypeObject NativeBitsType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "tsrkit_types._native.NativeBits",
    .tp_basicsize = sizeof(NativeBits),
    .tp_dealloc = (destructor)NativeBits_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = NativeBits_new,
    .tp_init = (initproc)NativeBits_init,
    .tp_as_sequence = &NativeBits_as_sequence,
    .tp_as_mapping = &NativeBits_as_mapping,
    .tp_methods = NativeBits_methods,
    .tp_repr = NativeBits_repr,
    .tp_richcompare = NativeBits_richcompare,
    .tp_iter = PySeqIter_New,
};

/* --------------------------- NativeTypedSeq --------------------------- */

typedef struct {
    PyObject_HEAD
    Py_ssize_t length;
    Py_ssize_t capacity;
    int byte_size;
    PyObject *element_type;
    unsigned char *data;
} NativeTypedSeq;

static int
nativeseq_get_element_type(PyObject *type, PyObject **elem_type_out, int *byte_size_out) {
    PyObject *elem_type = PyObject_GetAttrString(type, "_element_type");
    if (!elem_type) {
        PyErr_SetString(PyExc_TypeError, "Missing _element_type");
        return -1;
    }
    if (!PyType_Check(elem_type)) {
        Py_DECREF(elem_type);
        PyErr_SetString(PyExc_TypeError, "_element_type must be a type");
        return -1;
    }
    PyObject *byte_size_obj = PyObject_GetAttrString(elem_type, "byte_size");
    if (!byte_size_obj || !PyLong_Check(byte_size_obj)) {
        Py_XDECREF(byte_size_obj);
        Py_DECREF(elem_type);
        PyErr_SetString(PyExc_TypeError, "element type missing byte_size");
        return -1;
    }
    int byte_size = (int)PyLong_AsLong(byte_size_obj);
    Py_DECREF(byte_size_obj);
    if (PyErr_Occurred()) {
        Py_DECREF(elem_type);
        return -1;
    }
    if (byte_size <= 0) {
        Py_DECREF(elem_type);
        PyErr_SetString(PyExc_TypeError, "element type byte_size must be > 0");
        return -1;
    }
    *elem_type_out = elem_type;
    *byte_size_out = byte_size;
    return 0;
}

static int
nativeseq_check_length(NativeTypedSeq *self, Py_ssize_t new_len) {
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    PyObject *type = (PyObject *)Py_TYPE(self);
    if (get_class_ssize_attr(type, "_min_length", &min_len, 0) < 0) {
        return -1;
    }
    if (get_class_ssize_attr(type, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        return -1;
    }
    if (new_len < min_len) {
        PyErr_Format(PyExc_ValueError, "Vector: Expected sequence size to be >= %zd, resultant size %zd", min_len, new_len);
        return -1;
    }
    if (new_len > max_len) {
        PyErr_Format(PyExc_ValueError, "Vector: Expected sequence size to be <= %zd, resultant size %zd", max_len, new_len);
        return -1;
    }
    return 0;
}

static int
nativeseq_ensure_capacity(NativeTypedSeq *self, Py_ssize_t new_len) {
    if (new_len <= self->capacity) {
        return 0;
    }
    Py_ssize_t new_cap = self->capacity ? self->capacity : 4;
    while (new_cap < new_len) {
        new_cap *= 2;
    }
    Py_ssize_t new_bytes = new_cap * self->byte_size;
    Py_ssize_t old_bytes = self->capacity * self->byte_size;
    unsigned char *new_data = (unsigned char *)PyMem_Realloc(self->data, new_bytes);
    if (!new_data) {
        PyErr_NoMemory();
        return -1;
    }
    if (new_bytes > old_bytes) {
        memset(new_data + old_bytes, 0, (size_t)(new_bytes - old_bytes));
    }
    self->data = new_data;
    self->capacity = new_cap;
    return 0;
}

static unsigned long long
nativeseq_load_value(const unsigned char *data, int byte_size) {
    unsigned long long value = 0;
    for (int i = 0; i < byte_size; i++) {
        value |= ((unsigned long long)data[i]) << (8 * i);
    }
    return value;
}

static void
nativeseq_store_value(unsigned char *data, int byte_size, unsigned long long value) {
    for (int i = 0; i < byte_size; i++) {
        data[i] = (unsigned char)((value >> (8 * i)) & 0xFF);
    }
}

static int
nativeseq_convert_value(PyObject *value, PyObject *elem_type, int byte_size, unsigned long long *out) {
    int ok = PyObject_IsInstance(value, elem_type);
    if (ok < 0) {
        return -1;
    }
    if (!ok) {
        PyErr_Format(PyExc_TypeError, "%R is not an instance of %R", value, elem_type);
        return -1;
    }
    unsigned long long v = PyLong_AsUnsignedLongLong(value);
    if (PyErr_Occurred()) {
        return -1;
    }
    if (byte_size < 8) {
        unsigned long long max_val = (1ULL << (byte_size * 8)) - 1;
        if (v > max_val) {
            PyErr_SetString(PyExc_ValueError, "value out of range");
            return -1;
        }
    }
    *out = v;
    return 0;
}

static int
nativeseq_rebuild_from_sequence(NativeTypedSeq *seq, PyObject *seq_obj) {
    PyObject *items = PySequence_Fast(seq_obj, "values must be a sequence");
    if (!items) {
        return -1;
    }
    Py_ssize_t count = PySequence_Fast_GET_SIZE(items);
    if (nativeseq_ensure_capacity(seq, count) < 0) {
        Py_DECREF(items);
        return -1;
    }
    PyObject **vals = PySequence_Fast_ITEMS(items);
    for (Py_ssize_t i = 0; i < count; i++) {
        unsigned long long v = 0;
        if (nativeseq_convert_value(vals[i], seq->element_type, seq->byte_size, &v) < 0) {
            Py_DECREF(items);
            return -1;
        }
        nativeseq_store_value(seq->data + i * seq->byte_size, seq->byte_size, v);
    }
    seq->length = count;
    Py_DECREF(items);
    if (nativeseq_check_length(seq, seq->length) < 0) {
        return -1;
    }
    return 0;
}

static void
NativeTypedSeq_dealloc(NativeTypedSeq *self) {
    PyMem_Free(self->data);
    Py_XDECREF(self->element_type);
    Py_TYPE(self)->tp_free((PyObject *)self);
}

static PyObject *
NativeTypedSeq_new(PyTypeObject *type, PyObject *args, PyObject *kwds) {
    NativeTypedSeq *self = (NativeTypedSeq *)type->tp_alloc(type, 0);
    if (!self) {
        return NULL;
    }
    self->length = 0;
    self->capacity = 0;
    self->byte_size = 0;
    self->element_type = NULL;
    self->data = NULL;
    return (PyObject *)self;
}

static int
NativeTypedSeq_init(NativeTypedSeq *self, PyObject *args, PyObject *kwds) {
    PyObject *seq_obj = NULL;
    if (!PyArg_ParseTuple(args, "|O", &seq_obj)) {
        return -1;
    }
    PyObject *elem_type = NULL;
    int byte_size = 0;
    if (nativeseq_get_element_type((PyObject *)Py_TYPE(self), &elem_type, &byte_size) < 0) {
        return -1;
    }
    self->element_type = elem_type;
    self->byte_size = byte_size;

    if (!seq_obj) {
        if (nativeseq_check_length(self, 0) < 0) {
            return -1;
        }
        return 0;
    }
    PyObject *seq = PySequence_Fast(seq_obj, "values must be a sequence");
    if (!seq) {
        return -1;
    }
    Py_ssize_t seq_len = PySequence_Fast_GET_SIZE(seq);
    if (nativeseq_ensure_capacity(self, seq_len) < 0) {
        Py_DECREF(seq);
        return -1;
    }
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < seq_len; i++) {
        unsigned long long value = 0;
        if (nativeseq_convert_value(items[i], self->element_type, self->byte_size, &value) < 0) {
            Py_DECREF(seq);
            return -1;
        }
        nativeseq_store_value(self->data + i * self->byte_size, self->byte_size, value);
    }
    self->length = seq_len;
    Py_DECREF(seq);
    if (nativeseq_check_length(self, self->length) < 0) {
        return -1;
    }
    return 0;
}

static Py_ssize_t
NativeTypedSeq_len(PyObject *self) {
    return ((NativeTypedSeq *)self)->length;
}

static PyObject *
NativeTypedSeq_item(PyObject *self, Py_ssize_t idx) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    if (idx < 0) {
        idx += seq->length;
    }
    if (idx < 0 || idx >= seq->length) {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return NULL;
    }
    unsigned long long value = nativeseq_load_value(seq->data + idx * seq->byte_size, seq->byte_size);
    PyObject *val_obj = PyLong_FromUnsignedLongLong(value);
    if (!val_obj) {
        return NULL;
    }
    PyObject *typed = PyObject_CallFunctionObjArgs(seq->element_type, val_obj, NULL);
    Py_DECREF(val_obj);
    return typed;
}

static int
NativeTypedSeq_ass_item(PyObject *self, Py_ssize_t idx, PyObject *value) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    if (idx < 0) {
        idx += seq->length;
    }
    if (idx < 0 || idx >= seq->length) {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return -1;
    }
    unsigned long long v = 0;
    if (nativeseq_convert_value(value, seq->element_type, seq->byte_size, &v) < 0) {
        return -1;
    }
    nativeseq_store_value(seq->data + idx * seq->byte_size, seq->byte_size, v);
    return 0;
}

static PyObject *
NativeTypedSeq_subscript(PyObject *self, PyObject *item) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    if (PyIndex_Check(item)) {
        Py_ssize_t idx = PyNumber_AsSsize_t(item, PyExc_IndexError);
        if (idx == -1 && PyErr_Occurred()) {
            return NULL;
        }
        return NativeTypedSeq_item(self, idx);
    }
    if (PySlice_Check(item)) {
        Py_ssize_t start, stop, step, slicelen;
        if (PySlice_GetIndicesEx(item, seq->length, &start, &stop, &step, &slicelen) < 0) {
            return NULL;
        }
        PyObject *list = PyList_New(slicelen);
        if (!list) {
            return NULL;
        }
        for (Py_ssize_t i = 0; i < slicelen; i++) {
            Py_ssize_t idx = start + i * step;
            PyObject *val = NativeTypedSeq_item(self, idx);
            if (!val) {
                Py_DECREF(list);
                return NULL;
            }
            PyList_SET_ITEM(list, i, val);
        }
        return list;
    }
    PyErr_SetString(PyExc_TypeError, "indices must be int or slice");
    return NULL;
}

static int
NativeTypedSeq_ass_subscript(PyObject *self, PyObject *item, PyObject *value) {
    if (PyIndex_Check(item)) {
        Py_ssize_t idx = PyNumber_AsSsize_t(item, PyExc_IndexError);
        if (idx == -1 && PyErr_Occurred()) {
            return -1;
        }
        return NativeTypedSeq_ass_item(self, idx, value);
    }
    if (PySlice_Check(item)) {
        NativeTypedSeq *seq = (NativeTypedSeq *)self;
        PyObject *list = PyList_New(seq->length);
        if (!list) {
            return -1;
        }
        for (Py_ssize_t i = 0; i < seq->length; i++) {
            PyObject *val = NativeTypedSeq_item(self, i);
            if (!val) {
                Py_DECREF(list);
                return -1;
            }
            PyList_SET_ITEM(list, i, val);
        }
        if (PyObject_SetItem(list, item, value) < 0) {
            Py_DECREF(list);
            return -1;
        }
        int rc = nativeseq_rebuild_from_sequence(seq, list);
        Py_DECREF(list);
        return rc;
    }
    PyErr_SetString(PyExc_TypeError, "indices must be int or slice");
    return -1;
}

static PyObject *
NativeTypedSeq_append(PyObject *self, PyObject *args) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    PyObject *value;
    if (!PyArg_ParseTuple(args, "O", &value)) {
        return NULL;
    }
    unsigned long long v = 0;
    if (nativeseq_convert_value(value, seq->element_type, seq->byte_size, &v) < 0) {
        return NULL;
    }
    Py_ssize_t new_len = seq->length + 1;
    if (nativeseq_check_length(seq, new_len) < 0) {
        return NULL;
    }
    if (nativeseq_ensure_capacity(seq, new_len) < 0) {
        return NULL;
    }
    nativeseq_store_value(seq->data + seq->length * seq->byte_size, seq->byte_size, v);
    seq->length = new_len;
    Py_RETURN_NONE;
}

static PyObject *
NativeTypedSeq_extend(PyObject *self, PyObject *args) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    PyObject *seq_obj;
    if (!PyArg_ParseTuple(args, "O", &seq_obj)) {
        return NULL;
    }
    PyObject *items = PySequence_Fast(seq_obj, "values must be a sequence");
    if (!items) {
        return NULL;
    }
    Py_ssize_t count = PySequence_Fast_GET_SIZE(items);
    Py_ssize_t new_len = seq->length + count;
    if (nativeseq_check_length(seq, new_len) < 0) {
        Py_DECREF(items);
        return NULL;
    }
    if (nativeseq_ensure_capacity(seq, new_len) < 0) {
        Py_DECREF(items);
        return NULL;
    }
    PyObject **vals = PySequence_Fast_ITEMS(items);
    for (Py_ssize_t i = 0; i < count; i++) {
        unsigned long long v = 0;
        if (nativeseq_convert_value(vals[i], seq->element_type, seq->byte_size, &v) < 0) {
            Py_DECREF(items);
            return NULL;
        }
        nativeseq_store_value(seq->data + (seq->length + i) * seq->byte_size, seq->byte_size, v);
    }
    seq->length = new_len;
    Py_DECREF(items);
    Py_RETURN_NONE;
}

static PyObject *
NativeTypedSeq_insert(PyObject *self, PyObject *args) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    Py_ssize_t idx;
    PyObject *value;
    if (!PyArg_ParseTuple(args, "nO", &idx, &value)) {
        return NULL;
    }
    unsigned long long v = 0;
    if (nativeseq_convert_value(value, seq->element_type, seq->byte_size, &v) < 0) {
        return NULL;
    }
    if (idx < 0) {
        idx += seq->length;
    }
    if (idx < 0) {
        idx = 0;
    }
    if (idx > seq->length) {
        idx = seq->length;
    }
    Py_ssize_t new_len = seq->length + 1;
    if (nativeseq_check_length(seq, new_len) < 0) {
        return NULL;
    }
    if (nativeseq_ensure_capacity(seq, new_len) < 0) {
        return NULL;
    }
    memmove(seq->data + (idx + 1) * seq->byte_size,
            seq->data + idx * seq->byte_size,
            (size_t)((seq->length - idx) * seq->byte_size));
    nativeseq_store_value(seq->data + idx * seq->byte_size, seq->byte_size, v);
    seq->length = new_len;
    Py_RETURN_NONE;
}

static PyObject *
NativeTypedSeq_pop(PyObject *self, PyObject *args) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    Py_ssize_t idx = -1;
    if (!PyArg_ParseTuple(args, "|n", &idx)) {
        return NULL;
    }
    if (seq->length == 0) {
        PyErr_SetString(PyExc_IndexError, "pop from empty sequence");
        return NULL;
    }
    if (idx < 0) {
        idx += seq->length;
    }
    if (idx < 0 || idx >= seq->length) {
        PyErr_SetString(PyExc_IndexError, "index out of range");
        return NULL;
    }
    unsigned long long value = nativeseq_load_value(seq->data + idx * seq->byte_size, seq->byte_size);
    memmove(seq->data + idx * seq->byte_size,
            seq->data + (idx + 1) * seq->byte_size,
            (size_t)((seq->length - idx - 1) * seq->byte_size));
    seq->length -= 1;
    if (nativeseq_check_length(seq, seq->length) < 0) {
        return NULL;
    }
    PyObject *val_obj = PyLong_FromUnsignedLongLong(value);
    if (!val_obj) {
        return NULL;
    }
    PyObject *typed = PyObject_CallFunctionObjArgs(seq->element_type, val_obj, NULL);
    Py_DECREF(val_obj);
    return typed;
}

static PyObject *
NativeTypedSeq_repr(PyObject *self) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    PyObject *list = PyList_New(seq->length);
    if (!list) {
        return NULL;
    }
    for (Py_ssize_t i = 0; i < seq->length; i++) {
        PyObject *val = NativeTypedSeq_item(self, i);
        if (!val) {
            Py_DECREF(list);
            return NULL;
        }
        PyList_SET_ITEM(list, i, val);
    }
    PyObject *list_repr = PyObject_Repr(list);
    Py_DECREF(list);
    if (!list_repr) {
        return NULL;
    }
    PyObject *name = PyObject_GetAttrString((PyObject *)Py_TYPE(self), "__name__");
    if (!name) {
        Py_DECREF(list_repr);
        return NULL;
    }
    PyObject *result = PyUnicode_FromFormat("%S(%S)", name, list_repr);
    Py_DECREF(name);
    Py_DECREF(list_repr);
    return result;
}

static int
nativeseq_compare(NativeTypedSeq *seq, PyObject *other) {
    if (!PySequence_Check(other)) {
        return -2;
    }
    PyObject *seq_obj = PySequence_Fast(other, "comparison requires a sequence");
    if (!seq_obj) {
        return -1;
    }
    Py_ssize_t other_len = PySequence_Fast_GET_SIZE(seq_obj);
    if (other_len != seq->length) {
        Py_DECREF(seq_obj);
        return 0;
    }
    PyObject **items = PySequence_Fast_ITEMS(seq_obj);
    for (Py_ssize_t i = 0; i < seq->length; i++) {
        unsigned long long value = nativeseq_load_value(seq->data + i * seq->byte_size, seq->byte_size);
        PyObject *val_obj = PyLong_FromUnsignedLongLong(value);
        if (!val_obj) {
            Py_DECREF(seq_obj);
            return -1;
        }
        int eq = PyObject_RichCompareBool(items[i], val_obj, Py_EQ);
        Py_DECREF(val_obj);
        if (eq < 0) {
            Py_DECREF(seq_obj);
            return -1;
        }
        if (!eq) {
            Py_DECREF(seq_obj);
            return 0;
        }
    }
    Py_DECREF(seq_obj);
    return 1;
}

static PyObject *
NativeTypedSeq_richcompare(PyObject *self, PyObject *other, int op) {
    if (op != Py_EQ && op != Py_NE) {
        Py_RETURN_NOTIMPLEMENTED;
    }
    int eq = nativeseq_compare((NativeTypedSeq *)self, other);
    if (eq == -2) {
        Py_RETURN_NOTIMPLEMENTED;
    }
    if (eq < 0) {
        return NULL;
    }
    if (op == Py_NE) {
        eq = !eq;
    }
    return PyBool_FromLong(eq);
}

static PyObject *
NativeTypedSeq_encode_size(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    PyObject *type = (PyObject *)Py_TYPE(self);
    if (get_class_ssize_attr(type, "_min_length", &min_len, 0) < 0) {
        return NULL;
    }
    if (get_class_ssize_attr(type, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        return NULL;
    }
    Py_ssize_t payload = seq->length * seq->byte_size;
    if (min_len == max_len && min_len > 0) {
        return PyLong_FromSsize_t(payload);
    }
    int prefix = varint_size_ull((unsigned long long)seq->length);
    if (prefix < 0) {
        PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
        return NULL;
    }
    return PyLong_FromSsize_t(payload + prefix);
}

static PyObject *
NativeTypedSeq_encode(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    PyObject *type = (PyObject *)Py_TYPE(self);
    if (get_class_ssize_attr(type, "_min_length", &min_len, 0) < 0) {
        return NULL;
    }
    if (get_class_ssize_attr(type, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        return NULL;
    }
    int prefix = 0;
    if (!(min_len == max_len && min_len > 0)) {
        prefix = varint_size_ull((unsigned long long)seq->length);
        if (prefix < 0) {
            PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
            return NULL;
        }
    }
    Py_ssize_t payload = seq->length * seq->byte_size;
    PyObject *out = PyBytes_FromStringAndSize(NULL, payload + prefix);
    if (!out) {
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyBytes_AS_STRING(out);
    Py_ssize_t offset = 0;
    if (prefix > 0) {
        int wrote = encode_varint_ull((unsigned long long)seq->length, buf, prefix);
        if (wrote < 0) {
            Py_DECREF(out);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to encode length");
            return NULL;
        }
        offset = wrote;
    }
    if (payload > 0) {
        memcpy(buf + offset, seq->data, (size_t)payload);
    }
    return out;
}

static PyObject *
NativeTypedSeq_encode_into(PyObject *self, PyObject *args, PyObject *kwargs) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    static char *kwlist[] = {"buffer", "offset", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|n", kwlist, &buf_obj, &offset)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_WRITABLE) != 0) {
        return NULL;
    }
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    PyObject *type = (PyObject *)Py_TYPE(self);
    if (get_class_ssize_attr(type, "_min_length", &min_len, 0) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    if (get_class_ssize_attr(type, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    int prefix = 0;
    if (!(min_len == max_len && min_len > 0)) {
        prefix = varint_size_ull((unsigned long long)seq->length);
        if (prefix < 0) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
            return NULL;
        }
    }
    Py_ssize_t payload = seq->length * seq->byte_size;
    Py_ssize_t total = prefix + payload;
    if (offset < 0 || offset + total > view.len) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to encode value");
        return NULL;
    }
    unsigned char *buf = (unsigned char *)view.buf + offset;
    if (prefix > 0) {
        int wrote = encode_varint_ull((unsigned long long)seq->length, buf, prefix);
        if (wrote < 0) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to encode length");
            return NULL;
        }
        buf += wrote;
    }
    if (payload > 0) {
        memcpy(buf, seq->data, (size_t)payload);
    }
    PyBuffer_Release(&view);
    return PyLong_FromSsize_t(total);
}

static PyObject *
NativeTypedSeq_decode_from(PyObject *cls, PyObject *args) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    if (!PyArg_ParseTuple(args, "O|n", &buf_obj, &offset)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) != 0) {
        return NULL;
    }
    Py_ssize_t min_len = 0;
    Py_ssize_t max_len = (Py_ssize_t)((unsigned long long)1 << 63);
    if (get_class_ssize_attr(cls, "_min_length", &min_len, 0) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    if (get_class_ssize_attr(cls, "_max_length", &max_len, (Py_ssize_t)((unsigned long long)1 << 63)) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    const unsigned char *buf = (const unsigned char *)view.buf + offset;
    Py_ssize_t remaining = view.len - offset;
    unsigned long long length = 0;
    Py_ssize_t prefix = 0;
    if (min_len == max_len && min_len > 0) {
        length = (unsigned long long)min_len;
    } else {
        if (decode_varint_ull(buf, remaining, &length, &prefix) < 0) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to decode length");
            return NULL;
        }
        buf += prefix;
        remaining -= prefix;
    }
    if (length > (unsigned long long)PY_SSIZE_T_MAX) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Sequence too large to decode");
        return NULL;
    }
    if (length < (unsigned long long)min_len || length > (unsigned long long)max_len) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Sequence length out of bounds");
        return NULL;
    }
    PyObject *elem_type = NULL;
    int byte_size = 0;
    if (nativeseq_get_element_type(cls, &elem_type, &byte_size) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    Py_DECREF(elem_type);
    Py_ssize_t payload = (Py_ssize_t)length * byte_size;
    if (remaining < payload) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to decode sequence");
        return NULL;
    }
    NativeTypedSeq *self = (NativeTypedSeq *)NativeTypedSeq_new((PyTypeObject *)cls, NULL, NULL);
    if (!self) {
        PyBuffer_Release(&view);
        return NULL;
    }
    self->byte_size = byte_size;
    self->element_type = PyObject_GetAttrString(cls, "_element_type");
    if (!self->element_type) {
        PyBuffer_Release(&view);
        Py_DECREF(self);
        return NULL;
    }
    if (nativeseq_ensure_capacity(self, (Py_ssize_t)length) < 0) {
        PyBuffer_Release(&view);
        Py_DECREF(self);
        return NULL;
    }
    self->length = (Py_ssize_t)length;
    if (payload > 0) {
        memcpy(self->data, buf, (size_t)payload);
    }
    PyBuffer_Release(&view);
    return Py_BuildValue("Nn", (PyObject *)self, prefix + payload);
}

static PyObject *
NativeTypedSeq_decode(PyObject *cls, PyObject *args) {
    PyObject *tuple = NativeTypedSeq_decode_from(cls, args);
    if (!tuple) {
        return NULL;
    }
    if (!PyTuple_Check(tuple) || PyTuple_GET_SIZE(tuple) < 1) {
        Py_DECREF(tuple);
        PyErr_SetString(PyExc_ValueError, "Invalid decode_from result");
        return NULL;
    }
    PyObject *value = PyTuple_GET_ITEM(tuple, 0);
    Py_INCREF(value);
    Py_DECREF(tuple);
    return value;
}

static PyObject *
NativeTypedSeq_to_json(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    NativeTypedSeq *seq = (NativeTypedSeq *)self;
    PyObject *list = PyList_New(seq->length);
    if (!list) {
        return NULL;
    }
    for (Py_ssize_t i = 0; i < seq->length; i++) {
        unsigned long long value = nativeseq_load_value(seq->data + i * seq->byte_size, seq->byte_size);
        PyObject *val = PyLong_FromUnsignedLongLong(value);
        if (!val) {
            Py_DECREF(list);
            return NULL;
        }
        PyList_SET_ITEM(list, i, val);
    }
    return list;
}

static PyObject *
NativeTypedSeq_from_json(PyObject *cls, PyObject *args) {
    PyObject *seq_obj;
    if (!PyArg_ParseTuple(args, "O", &seq_obj)) {
        return NULL;
    }
    PyObject *elem_type = NULL;
    int byte_size = 0;
    if (nativeseq_get_element_type(cls, &elem_type, &byte_size) < 0) {
        return NULL;
    }
    Py_DECREF(elem_type);
    PyObject *seq = PySequence_Fast(seq_obj, "values must be a sequence");
    if (!seq) {
        return NULL;
    }
    NativeTypedSeq *self = (NativeTypedSeq *)NativeTypedSeq_new((PyTypeObject *)cls, NULL, NULL);
    if (!self) {
        Py_DECREF(seq);
        return NULL;
    }
    self->element_type = PyObject_GetAttrString(cls, "_element_type");
    if (!self->element_type) {
        Py_DECREF(seq);
        Py_DECREF(self);
        return NULL;
    }
    self->byte_size = byte_size;
    Py_ssize_t count = PySequence_Fast_GET_SIZE(seq);
    if (nativeseq_ensure_capacity(self, count) < 0) {
        Py_DECREF(seq);
        Py_DECREF(self);
        return NULL;
    }
    PyObject **items = PySequence_Fast_ITEMS(seq);
    for (Py_ssize_t i = 0; i < count; i++) {
        PyObject *val_obj = PyObject_CallMethod(self->element_type, "from_json", "O", items[i]);
        if (!val_obj) {
            Py_DECREF(seq);
            Py_DECREF(self);
            return NULL;
        }
        unsigned long long v = 0;
        if (nativeseq_convert_value(val_obj, self->element_type, self->byte_size, &v) < 0) {
            Py_DECREF(val_obj);
            Py_DECREF(seq);
            Py_DECREF(self);
            return NULL;
        }
        Py_DECREF(val_obj);
        nativeseq_store_value(self->data + i * self->byte_size, self->byte_size, v);
    }
    self->length = count;
    Py_DECREF(seq);
    if (nativeseq_check_length(self, self->length) < 0) {
        Py_DECREF(self);
        return NULL;
    }
    return (PyObject *)self;
}

static PyMethodDef NativeTypedSeq_methods[] = {
    {"append", NativeTypedSeq_append, METH_VARARGS, "Append a value."},
    {"extend", NativeTypedSeq_extend, METH_VARARGS, "Extend with a sequence."},
    {"insert", NativeTypedSeq_insert, METH_VARARGS, "Insert a value."},
    {"pop", NativeTypedSeq_pop, METH_VARARGS, "Pop a value."},
    {"encode_size", NativeTypedSeq_encode_size, METH_NOARGS, "Encoded size."},
    {"encode", NativeTypedSeq_encode, METH_NOARGS, "Encode to bytes."},
    {"encode_into", (PyCFunction)NativeTypedSeq_encode_into, METH_VARARGS | METH_KEYWORDS, "Encode into buffer."},
    {"decode_from", NativeTypedSeq_decode_from, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {"decode", NativeTypedSeq_decode, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {"to_json", NativeTypedSeq_to_json, METH_NOARGS, "Convert to JSON."},
    {"from_json", NativeTypedSeq_from_json, METH_CLASS | METH_VARARGS, "Create from JSON."},
    {NULL, NULL, 0, NULL},
};

static PySequenceMethods NativeTypedSeq_as_sequence = {
    .sq_length = NativeTypedSeq_len,
    .sq_item = (ssizeargfunc)NativeTypedSeq_item,
    .sq_ass_item = (ssizeobjargproc)NativeTypedSeq_ass_item,
};

static PyMappingMethods NativeTypedSeq_as_mapping = {
    .mp_length = NativeTypedSeq_len,
    .mp_subscript = NativeTypedSeq_subscript,
    .mp_ass_subscript = NativeTypedSeq_ass_subscript,
};

static PyTypeObject NativeTypedSeqType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "tsrkit_types._native.NativeTypedSeq",
    .tp_basicsize = sizeof(NativeTypedSeq),
    .tp_dealloc = (destructor)NativeTypedSeq_dealloc,
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_new = NativeTypedSeq_new,
    .tp_init = (initproc)NativeTypedSeq_init,
    .tp_as_sequence = &NativeTypedSeq_as_sequence,
    .tp_as_mapping = &NativeTypedSeq_as_mapping,
    .tp_methods = NativeTypedSeq_methods,
    .tp_repr = NativeTypedSeq_repr,
    .tp_richcompare = NativeTypedSeq_richcompare,
    .tp_iter = PySeqIter_New,
};

/* ------------------------------- NativeBytes ------------------------------ */

static PyObject *
NativeBytes_encode_size(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    Py_ssize_t fixed_len = 0;
    int is_fixed = 0;
    if (get_class_optional_length((PyObject *)Py_TYPE(self), &fixed_len, &is_fixed) < 0) {
        return NULL;
    }
    Py_ssize_t size = PyBytes_GET_SIZE(self);
    if (is_fixed) {
        return PyLong_FromSsize_t(fixed_len);
    }
    int prefix = varint_size_ull((unsigned long long)size);
    if (prefix < 0) {
        PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
        return NULL;
    }
    return PyLong_FromSsize_t((Py_ssize_t)prefix + size);
}

static PyObject *
NativeBytes_encode_into(PyObject *self, PyObject *args, PyObject *kwargs) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    static char *kwlist[] = {"buffer", "offset", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|n", kwlist, &buf_obj, &offset)) {
        return NULL;
    }
    if (!PyByteArray_Check(buf_obj)) {
        PyErr_SetString(PyExc_TypeError, "buffer must be bytearray");
        return NULL;
    }
    Py_ssize_t fixed_len = 0;
    int is_fixed = 0;
    if (get_class_optional_length((PyObject *)Py_TYPE(self), &fixed_len, &is_fixed) < 0) {
        return NULL;
    }
    Py_ssize_t size = PyBytes_GET_SIZE(self);
    if (is_fixed && size != fixed_len) {
        PyErr_SetString(PyExc_ValueError, "Byte sequence length mismatch");
        return NULL;
    }
    int prefix = 0;
    if (!is_fixed) {
        prefix = varint_size_ull((unsigned long long)size);
        if (prefix < 0) {
            PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
            return NULL;
        }
    }
    Py_ssize_t total = size + prefix;
    Py_ssize_t buf_len = PyByteArray_Size(buf_obj);
    if (offset < 0 || offset + total > buf_len) {
        PyErr_SetString(PyExc_ValueError, "Buffer too small to encode value");
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyByteArray_AsString(buf_obj) + offset;
    if (prefix > 0) {
        int wrote = encode_varint_ull((unsigned long long)size, buf, buf_len - offset);
        if (wrote < 0) {
            PyErr_SetString(PyExc_ValueError, "Buffer too small to encode length");
            return NULL;
        }
        buf += wrote;
    }
    if (size > 0) {
        memcpy(buf, PyBytes_AS_STRING(self), (size_t)size);
    }
    return PyLong_FromSsize_t(total);
}

static PyObject *
NativeBytes_decode_from(PyObject *cls, PyObject *args) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    if (!PyArg_ParseTuple(args, "O|n", &buf_obj, &offset)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) != 0) {
        return NULL;
    }
    Py_ssize_t fixed_len = 0;
    int is_fixed = 0;
    if (get_class_optional_length(cls, &fixed_len, &is_fixed) < 0) {
        PyBuffer_Release(&view);
        return NULL;
    }
    const unsigned char *buf = (const unsigned char *)view.buf + offset;
    Py_ssize_t remaining = view.len - offset;
    unsigned long long length = 0;
    Py_ssize_t prefix = 0;
    if (is_fixed) {
        length = (unsigned long long)fixed_len;
    } else {
        if (decode_varint_ull(buf, remaining, &length, &prefix) < 0) {
            PyBuffer_Release(&view);
            PyErr_SetString(PyExc_ValueError, "Buffer too small to decode length");
            return NULL;
        }
        buf += prefix;
        remaining -= prefix;
    }
    if (length > (unsigned long long)PY_SSIZE_T_MAX) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Bytes too large to decode");
        return NULL;
    }
    if (remaining < (Py_ssize_t)length) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_TypeError, "Insufficient buffer");
        return NULL;
    }
    PyObject *bytes_obj = PyBytes_FromStringAndSize((const char *)buf, (Py_ssize_t)length);
    PyBuffer_Release(&view);
    if (!bytes_obj) {
        return NULL;
    }
    PyObject *inst = PyObject_CallFunctionObjArgs(cls, bytes_obj, NULL);
    Py_DECREF(bytes_obj);
    if (!inst) {
        return NULL;
    }
    return Py_BuildValue("Nn", inst, prefix + (Py_ssize_t)length);
}

static PyObject *
NativeBytes_decode(PyObject *cls, PyObject *args) {
    PyObject *tuple = NativeBytes_decode_from(cls, args);
    if (!tuple) {
        return NULL;
    }
    if (!PyTuple_Check(tuple) || PyTuple_GET_SIZE(tuple) < 1) {
        Py_DECREF(tuple);
        PyErr_SetString(PyExc_ValueError, "Invalid decode_from result");
        return NULL;
    }
    PyObject *value = PyTuple_GET_ITEM(tuple, 0);
    Py_INCREF(value);
    Py_DECREF(tuple);
    return value;
}

static PyMethodDef NativeBytes_methods[] = {
    {"encode_size", NativeBytes_encode_size, METH_NOARGS, "Encoded size."},
    {"encode_into", (PyCFunction)NativeBytes_encode_into, METH_VARARGS | METH_KEYWORDS, "Encode into buffer."},
    {"decode_from", NativeBytes_decode_from, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {"decode", NativeBytes_decode, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {NULL, NULL, 0, NULL},
};

static PyTypeObject NativeBytesType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "tsrkit_types._native.NativeBytes",
    .tp_basicsize = sizeof(PyBytesObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_methods = NativeBytes_methods,
    .tp_base = &PyBytes_Type,
};

/* ----------------------------- NativeByteArray ---------------------------- */

static PyObject *
NativeByteArray_encode_size(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    Py_ssize_t size = PyByteArray_Size(self);
    int prefix = varint_size_ull((unsigned long long)size);
    if (prefix < 0) {
        PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
        return NULL;
    }
    return PyLong_FromSsize_t((Py_ssize_t)prefix + size);
}

static PyObject *
NativeByteArray_encode_into(PyObject *self, PyObject *args, PyObject *kwargs) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    static char *kwlist[] = {"buffer", "offset", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|n", kwlist, &buf_obj, &offset)) {
        return NULL;
    }
    if (!PyByteArray_Check(buf_obj)) {
        PyErr_SetString(PyExc_TypeError, "buffer must be bytearray");
        return NULL;
    }
    Py_ssize_t size = PyByteArray_Size(self);
    int prefix = varint_size_ull((unsigned long long)size);
    if (prefix < 0) {
        PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
        return NULL;
    }
    Py_ssize_t total = size + prefix;
    Py_ssize_t buf_len = PyByteArray_Size(buf_obj);
    if (offset < 0 || offset + total > buf_len) {
        PyErr_SetString(PyExc_ValueError, "Buffer too small to encode value");
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyByteArray_AsString(buf_obj) + offset;
    int wrote = encode_varint_ull((unsigned long long)size, buf, buf_len - offset);
    if (wrote < 0) {
        PyErr_SetString(PyExc_ValueError, "Buffer too small to encode length");
        return NULL;
    }
    buf += wrote;
    if (size > 0) {
        memcpy(buf, PyByteArray_AsString(self), (size_t)size);
    }
    return PyLong_FromSsize_t(total);
}

static PyObject *
NativeByteArray_decode_from(PyObject *cls, PyObject *args) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    if (!PyArg_ParseTuple(args, "O|n", &buf_obj, &offset)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) != 0) {
        return NULL;
    }
    const unsigned char *buf = (const unsigned char *)view.buf + offset;
    Py_ssize_t remaining = view.len - offset;
    if (remaining < 0) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Offset out of bounds");
        return NULL;
    }
    if (remaining == 0) {
        PyBuffer_Release(&view);
        PyObject *inst = PyObject_CallNoArgs(cls);
        if (!inst) {
            return NULL;
        }
        return Py_BuildValue("Nn", inst, (Py_ssize_t)1);
    }
    unsigned long long length = 0;
    Py_ssize_t prefix = 0;
    if (decode_varint_ull(buf, remaining, &length, &prefix) < 0) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to decode length");
        return NULL;
    }
    buf += prefix;
    remaining -= prefix;
    if (length > (unsigned long long)PY_SSIZE_T_MAX) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_ValueError, "Bytearray too large to decode");
        return NULL;
    }
    if (remaining < (Py_ssize_t)length) {
        PyBuffer_Release(&view);
        PyErr_SetString(PyExc_TypeError, "Insufficient buffer");
        return NULL;
    }
    PyObject *ba = PyByteArray_FromStringAndSize((const char *)buf, (Py_ssize_t)length);
    PyBuffer_Release(&view);
    if (!ba) {
        return NULL;
    }
    PyObject *inst = PyObject_CallFunctionObjArgs(cls, ba, NULL);
    Py_DECREF(ba);
    if (!inst) {
        return NULL;
    }
    return Py_BuildValue("Nn", inst, prefix + (Py_ssize_t)length);
}

static PyObject *
NativeByteArray_decode(PyObject *cls, PyObject *args) {
    PyObject *tuple = NativeByteArray_decode_from(cls, args);
    if (!tuple) {
        return NULL;
    }
    if (!PyTuple_Check(tuple) || PyTuple_GET_SIZE(tuple) < 1) {
        Py_DECREF(tuple);
        PyErr_SetString(PyExc_ValueError, "Invalid decode_from result");
        return NULL;
    }
    PyObject *value = PyTuple_GET_ITEM(tuple, 0);
    Py_INCREF(value);
    Py_DECREF(tuple);
    return value;
}

static PyMethodDef NativeByteArray_methods[] = {
    {"encode_size", NativeByteArray_encode_size, METH_NOARGS, "Encoded size."},
    {"encode_into", (PyCFunction)NativeByteArray_encode_into, METH_VARARGS | METH_KEYWORDS, "Encode into buffer."},
    {"decode_from", NativeByteArray_decode_from, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {"decode", NativeByteArray_decode, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {NULL, NULL, 0, NULL},
};

static PyTypeObject NativeByteArrayType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "tsrkit_types._native.NativeByteArray",
    .tp_basicsize = sizeof(PyByteArrayObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_methods = NativeByteArray_methods,
    .tp_base = &PyByteArray_Type,
};

/* ------------------------------ NativeDict ------------------------------- */

static int
dict_get_types(PyObject *type, PyObject **key_type, PyObject **value_type) {
    PyObject *kt = PyObject_GetAttrString(type, "_key_type");
    if (!kt) {
        PyErr_SetString(PyExc_TypeError, "Missing _key_type");
        return -1;
    }
    PyObject *vt = PyObject_GetAttrString(type, "_value_type");
    if (!vt) {
        Py_DECREF(kt);
        PyErr_SetString(PyExc_TypeError, "Missing _value_type");
        return -1;
    }
    if (!PyType_Check(kt) || !PyType_Check(vt)) {
        Py_DECREF(kt);
        Py_DECREF(vt);
        PyErr_SetString(PyExc_TypeError, "_key_type/_value_type must be types");
        return -1;
    }
    *key_type = kt;
    *value_type = vt;
    return 0;
}

static int
type_is_string(PyObject *type, int *is_string) {
    *is_string = 0;
    if (!PyType_Check(type)) {
        return 0;
    }
    if (!PyType_IsSubtype((PyTypeObject *)type, &PyUnicode_Type)) {
        return 0;
    }
    PyObject *module = PyObject_GetAttrString(type, "__module__");
    if (!module) {
        PyErr_Clear();
        return 0;
    }
    int is_target = PyUnicode_Check(module) &&
                    PyUnicode_CompareWithASCIIString(module, "tsrkit_types.string") == 0;
    Py_DECREF(module);
    if (is_target) {
        *is_string = 1;
    }
    return 0;
}

static int
type_int_info(PyObject *type, int *byte_size, int *is_signed, int *is_int) {
    *is_int = 0;
    *byte_size = 0;
    *is_signed = 0;
    if (!PyType_Check(type)) {
        return 0;
    }
    if (!PyType_IsSubtype((PyTypeObject *)type, &PyLong_Type)) {
        return 0;
    }
    PyObject *bs = PyObject_GetAttrString(type, "byte_size");
    if (!bs) {
        PyErr_Clear();
        return 0;
    }
    if (!PyLong_Check(bs)) {
        Py_DECREF(bs);
        return 0;
    }
    int size = (int)PyLong_AsLong(bs);
    Py_DECREF(bs);
    if (PyErr_Occurred()) {
        return -1;
    }
    int signed_flag = 0;
    PyObject *sg = PyObject_GetAttrString(type, "signed");
    if (sg) {
        signed_flag = PyObject_IsTrue(sg);
        Py_DECREF(sg);
        if (signed_flag < 0) {
            return -1;
        }
    } else {
        PyErr_Clear();
    }
    *byte_size = size;
    *is_signed = signed_flag;
    *is_int = 1;
    return 0;
}

static PyObject *
NativeDict_encode_size(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    Py_ssize_t dict_len = PyDict_Size(self);
    int prefix = varint_size_ull((unsigned long long)dict_len);
    if (prefix < 0) {
        PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
        return NULL;
    }
    Py_ssize_t total = prefix;
    PyObject *keys = PyDict_Keys(self);
    if (!keys) {
        return NULL;
    }
    if (PyList_Sort(keys) < 0) {
        Py_DECREF(keys);
        return NULL;
    }
    Py_ssize_t count = PyList_GET_SIZE(keys);
    PyObject *key_type = NULL;
    PyObject *value_type = NULL;
    if (dict_get_types((PyObject *)Py_TYPE(self), &key_type, &value_type) < 0) {
        Py_DECREF(keys);
        return NULL;
    }
    int key_is_string = 0;
    int key_is_int = 0;
    int key_byte_size = 0;
    int key_signed = 0;
    if (type_is_string(key_type, &key_is_string) < 0) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        Py_DECREF(keys);
        return NULL;
    }
    if (type_int_info(key_type, &key_byte_size, &key_signed, &key_is_int) < 0) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        Py_DECREF(keys);
        return NULL;
    }
    int val_is_int = 0;
    int val_byte_size = 0;
    int val_signed = 0;
    if (type_int_info(value_type, &val_byte_size, &val_signed, &val_is_int) < 0) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        Py_DECREF(keys);
        return NULL;
    }
    for (Py_ssize_t i = 0; i < count; i++) {
        PyObject *key = PyList_GET_ITEM(keys, i);
        PyObject *value = PyDict_GetItem(self, key);
        if (!value) {
            Py_DECREF(key_type);
            Py_DECREF(value_type);
            Py_DECREF(keys);
            PyErr_SetString(PyExc_KeyError, "Key not found during encoding");
            return NULL;
        }
        if (key_is_string && val_is_int && !val_signed && val_byte_size <= 8) {
            Py_ssize_t key_len = 0;
            const char *key_buf = PyUnicode_AsUTF8AndSize(key, &key_len);
            if (!key_buf) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            int key_prefix = varint_size_ull((unsigned long long)key_len);
            if (key_prefix < 0) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                PyErr_SetString(PyExc_ValueError, "Key too large for encoding");
                return NULL;
            }
            total += key_prefix + key_len;
            if (val_byte_size > 0) {
                total += val_byte_size;
            } else {
                unsigned long long v = PyLong_AsUnsignedLongLong(value);
                if (PyErr_Occurred()) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    return NULL;
                }
                int val_prefix = varint_size_ull(v);
                if (val_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
                    return NULL;
                }
                total += val_prefix;
            }
        } else if (key_is_int && val_is_int && !key_signed && !val_signed && key_byte_size <= 8 && val_byte_size <= 8) {
            unsigned long long k = PyLong_AsUnsignedLongLong(key);
            if (PyErr_Occurred()) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            unsigned long long v = PyLong_AsUnsignedLongLong(value);
            if (PyErr_Occurred()) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            if (key_byte_size > 0) {
                total += key_byte_size;
            } else {
                int key_prefix = varint_size_ull(k);
                if (key_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Key too large for encoding");
                    return NULL;
                }
                total += key_prefix;
            }
            if (val_byte_size > 0) {
                total += val_byte_size;
            } else {
                int val_prefix = varint_size_ull(v);
                if (val_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
                    return NULL;
                }
                total += val_prefix;
            }
        } else {
            Py_ssize_t key_size = 0;
            Py_ssize_t val_size = 0;
            if (call_encode_size(key, &key_size) < 0 || call_encode_size(value, &val_size) < 0) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            total += key_size + val_size;
        }
    }
    Py_DECREF(key_type);
    Py_DECREF(value_type);
    Py_DECREF(keys);
    return PyLong_FromSsize_t(total);
}

static PyObject *
NativeDict_encode_into(PyObject *self, PyObject *args, PyObject *kwargs) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    static char *kwlist[] = {"buffer", "offset", NULL};
    if (!PyArg_ParseTupleAndKeywords(args, kwargs, "O|n", kwlist, &buf_obj, &offset)) {
        return NULL;
    }
    if (!PyByteArray_Check(buf_obj)) {
        PyErr_SetString(PyExc_TypeError, "buffer must be bytearray");
        return NULL;
    }
    Py_ssize_t dict_len = PyDict_Size(self);
    int prefix = varint_size_ull((unsigned long long)dict_len);
    if (prefix < 0) {
        PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
        return NULL;
    }
    PyObject *keys = PyDict_Keys(self);
    if (!keys) {
        return NULL;
    }
    if (PyList_Sort(keys) < 0) {
        Py_DECREF(keys);
        return NULL;
    }
    PyObject *key_type = NULL;
    PyObject *value_type = NULL;
    if (dict_get_types((PyObject *)Py_TYPE(self), &key_type, &value_type) < 0) {
        Py_DECREF(keys);
        return NULL;
    }
    int key_is_string = 0;
    int key_is_int = 0;
    int key_byte_size = 0;
    int key_signed = 0;
    if (type_is_string(key_type, &key_is_string) < 0) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        Py_DECREF(keys);
        return NULL;
    }
    if (type_int_info(key_type, &key_byte_size, &key_signed, &key_is_int) < 0) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        Py_DECREF(keys);
        return NULL;
    }
    int val_is_int = 0;
    int val_byte_size = 0;
    int val_signed = 0;
    if (type_int_info(value_type, &val_byte_size, &val_signed, &val_is_int) < 0) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        Py_DECREF(keys);
        return NULL;
    }
    Py_ssize_t total = prefix;
    Py_ssize_t count = PyList_GET_SIZE(keys);
    for (Py_ssize_t i = 0; i < count; i++) {
        PyObject *key = PyList_GET_ITEM(keys, i);
        PyObject *value = PyDict_GetItem(self, key);
        if (!value) {
            Py_DECREF(key_type);
            Py_DECREF(value_type);
            Py_DECREF(keys);
            PyErr_SetString(PyExc_KeyError, "Key not found during encoding");
            return NULL;
        }
        if (key_is_string && val_is_int && !val_signed && val_byte_size <= 8) {
            Py_ssize_t key_len = 0;
            const char *key_buf = PyUnicode_AsUTF8AndSize(key, &key_len);
            if (!key_buf) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            int key_prefix = varint_size_ull((unsigned long long)key_len);
            if (key_prefix < 0) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                PyErr_SetString(PyExc_ValueError, "Key too large for encoding");
                return NULL;
            }
            total += key_prefix + key_len;
            if (val_byte_size > 0) {
                total += val_byte_size;
            } else {
                unsigned long long v = PyLong_AsUnsignedLongLong(value);
                if (PyErr_Occurred()) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    return NULL;
                }
                int val_prefix = varint_size_ull(v);
                if (val_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
                    return NULL;
                }
                total += val_prefix;
            }
        } else if (key_is_int && val_is_int && !key_signed && !val_signed && key_byte_size <= 8 && val_byte_size <= 8) {
            unsigned long long k = PyLong_AsUnsignedLongLong(key);
            if (PyErr_Occurred()) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            unsigned long long v = PyLong_AsUnsignedLongLong(value);
            if (PyErr_Occurred()) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            if (key_byte_size > 0) {
                total += key_byte_size;
            } else {
                int key_prefix = varint_size_ull(k);
                if (key_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Key too large for encoding");
                    return NULL;
                }
                total += key_prefix;
            }
            if (val_byte_size > 0) {
                total += val_byte_size;
            } else {
                int val_prefix = varint_size_ull(v);
                if (val_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Value too large for encoding");
                    return NULL;
                }
                total += val_prefix;
            }
        } else {
            Py_ssize_t key_size = 0;
            Py_ssize_t val_size = 0;
            if (call_encode_size(key, &key_size) < 0 || call_encode_size(value, &val_size) < 0) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            total += key_size + val_size;
        }
    }
    Py_ssize_t buf_len = PyByteArray_Size(buf_obj);
    if (offset < 0 || offset + total > buf_len) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        Py_DECREF(keys);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to encode value");
        return NULL;
    }
    unsigned char *buf = (unsigned char *)PyByteArray_AsString(buf_obj) + offset;
    int wrote = encode_varint_ull((unsigned long long)dict_len, buf, buf_len - offset);
    if (wrote < 0) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        Py_DECREF(keys);
        PyErr_SetString(PyExc_ValueError, "Buffer too small to encode length");
        return NULL;
    }
    Py_ssize_t current_offset = offset + wrote;
    for (Py_ssize_t i = 0; i < count; i++) {
        PyObject *key = PyList_GET_ITEM(keys, i);
        PyObject *value = PyDict_GetItem(self, key);
        if (key_is_string && val_is_int && !val_signed && val_byte_size <= 8) {
            Py_ssize_t key_len = 0;
            const char *key_buf = PyUnicode_AsUTF8AndSize(key, &key_len);
            if (!key_buf) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            int key_prefix = encode_varint_ull((unsigned long long)key_len,
                                               (unsigned char *)PyByteArray_AsString(buf_obj) + current_offset,
                                               buf_len - current_offset);
            if (key_prefix < 0) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                PyErr_SetString(PyExc_ValueError, "Buffer too small to encode key");
                return NULL;
            }
            current_offset += key_prefix;
            if (key_len > 0) {
                memcpy(PyByteArray_AsString(buf_obj) + current_offset, key_buf, (size_t)key_len);
            }
            current_offset += key_len;
            if (val_byte_size > 0) {
                unsigned long long v = PyLong_AsUnsignedLongLong(value);
                if (PyErr_Occurred()) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    return NULL;
                }
                nativeseq_store_value((unsigned char *)PyByteArray_AsString(buf_obj) + current_offset, val_byte_size, v);
                current_offset += val_byte_size;
            } else {
                unsigned long long v = PyLong_AsUnsignedLongLong(value);
                if (PyErr_Occurred()) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    return NULL;
                }
                int val_prefix = encode_varint_ull(v,
                                                   (unsigned char *)PyByteArray_AsString(buf_obj) + current_offset,
                                                   buf_len - current_offset);
                if (val_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to encode value");
                    return NULL;
                }
                current_offset += val_prefix;
            }
        } else if (key_is_int && val_is_int && !key_signed && !val_signed && key_byte_size <= 8 && val_byte_size <= 8) {
            unsigned long long k = PyLong_AsUnsignedLongLong(key);
            if (PyErr_Occurred()) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            if (key_byte_size > 0) {
                nativeseq_store_value((unsigned char *)PyByteArray_AsString(buf_obj) + current_offset, key_byte_size, k);
                current_offset += key_byte_size;
            } else {
                int key_prefix = encode_varint_ull(k,
                                                   (unsigned char *)PyByteArray_AsString(buf_obj) + current_offset,
                                                   buf_len - current_offset);
                if (key_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to encode key");
                    return NULL;
                }
                current_offset += key_prefix;
            }
            unsigned long long v = PyLong_AsUnsignedLongLong(value);
            if (PyErr_Occurred()) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            if (val_byte_size > 0) {
                nativeseq_store_value((unsigned char *)PyByteArray_AsString(buf_obj) + current_offset, val_byte_size, v);
                current_offset += val_byte_size;
            } else {
                int val_prefix = encode_varint_ull(v,
                                                   (unsigned char *)PyByteArray_AsString(buf_obj) + current_offset,
                                                   buf_len - current_offset);
                if (val_prefix < 0) {
                    Py_DECREF(key_type);
                    Py_DECREF(value_type);
                    Py_DECREF(keys);
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to encode value");
                    return NULL;
                }
                current_offset += val_prefix;
            }
        } else {
            Py_ssize_t wrote_key = 0;
            if (call_encode_into(key, buf_obj, current_offset, &wrote_key) < 0) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            current_offset += wrote_key;
            Py_ssize_t wrote_val = 0;
            if (call_encode_into(value, buf_obj, current_offset, &wrote_val) < 0) {
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(keys);
                return NULL;
            }
            current_offset += wrote_val;
        }
    }
    Py_DECREF(key_type);
    Py_DECREF(value_type);
    Py_DECREF(keys);
    return PyLong_FromSsize_t(total);
}

static PyObject *
NativeDict_decode_from(PyObject *cls, PyObject *args) {
    PyObject *buf_obj;
    Py_ssize_t offset = 0;
    if (!PyArg_ParseTuple(args, "O|n", &buf_obj, &offset)) {
        return NULL;
    }
    Py_buffer view;
    if (PyObject_GetBuffer(buf_obj, &view, PyBUF_SIMPLE) != 0) {
        return NULL;
    }
    PyObject *key_type = NULL;
    PyObject *value_type = NULL;
    PyObject *result = NULL;
    PyObject *ret = NULL;

    if (offset < 0 || offset > view.len) {
        PyErr_SetString(PyExc_ValueError, "Offset out of bounds");
        goto error;
    }
    const unsigned char *base = (const unsigned char *)view.buf;
    Py_ssize_t buf_len = view.len;
    const unsigned char *buf = base + offset;
    Py_ssize_t remaining = buf_len - offset;
    unsigned long long length = 0;
    Py_ssize_t prefix = 0;
    if (decode_varint_ull(buf, remaining, &length, &prefix) < 0) {
        PyErr_SetString(PyExc_ValueError, "Buffer too small to decode length");
        goto error;
    }
    if (length > (unsigned long long)PY_SSIZE_T_MAX) {
        PyErr_SetString(PyExc_ValueError, "Dictionary too large to decode");
        goto error;
    }
    if (dict_get_types(cls, &key_type, &value_type) < 0) {
        goto error;
    }
    int key_is_string = 0;
    int key_is_int = 0;
    int key_byte_size = 0;
    int key_signed = 0;
    if (type_is_string(key_type, &key_is_string) < 0) {
        goto error;
    }
    if (type_int_info(key_type, &key_byte_size, &key_signed, &key_is_int) < 0) {
        goto error;
    }
    int val_is_int = 0;
    int val_byte_size = 0;
    int val_signed = 0;
    if (type_int_info(value_type, &val_byte_size, &val_signed, &val_is_int) < 0) {
        goto error;
    }
    result = PyObject_CallObject(cls, NULL);
    if (!result) {
        goto error;
    }
    Py_ssize_t current_offset = offset + prefix;
    for (Py_ssize_t i = 0; i < (Py_ssize_t)length; i++) {
        if (key_is_string && val_is_int && !val_signed && val_byte_size <= 8) {
            const unsigned char *buf2 = base + current_offset;
            Py_ssize_t remaining2 = buf_len - current_offset;
            unsigned long long key_len = 0;
            Py_ssize_t key_prefix = 0;
            if (decode_varint_ull(buf2, remaining2, &key_len, &key_prefix) < 0) {
                PyErr_SetString(PyExc_ValueError, "Buffer too small to decode key");
                goto error;
            }
            buf2 += key_prefix;
            remaining2 -= key_prefix;
            if (key_len > (unsigned long long)remaining2) {
                PyErr_SetString(PyExc_ValueError, "Buffer too small to decode key");
                goto error;
            }
            PyObject *key_str = PyUnicode_DecodeUTF8((const char *)buf2, (Py_ssize_t)key_len, NULL);
            if (!key_str) {
                goto error;
            }
            PyObject *key = PyObject_CallFunctionObjArgs(key_type, key_str, NULL);
            Py_DECREF(key_str);
            if (!key) {
                goto error;
            }
            current_offset += key_prefix + (Py_ssize_t)key_len;
            buf2 = base + current_offset;
            remaining2 = buf_len - current_offset;
            unsigned long long value_num = 0;
            Py_ssize_t value_size = 0;
            if (val_byte_size > 0) {
                if (remaining2 < val_byte_size) {
                    Py_DECREF(key);
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to decode value");
                    goto error;
                }
                value_num = nativeseq_load_value(buf2, val_byte_size);
                value_size = val_byte_size;
            } else {
                if (decode_varint_ull(buf2, remaining2, &value_num, &value_size) < 0) {
                    Py_DECREF(key);
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to decode value");
                    goto error;
                }
            }
            PyObject *val_num_obj = PyLong_FromUnsignedLongLong(value_num);
            if (!val_num_obj) {
                Py_DECREF(key);
                goto error;
            }
            PyObject *value = PyObject_CallFunctionObjArgs(value_type, val_num_obj, NULL);
            Py_DECREF(val_num_obj);
            if (!value) {
                Py_DECREF(key);
                goto error;
            }
            current_offset += value_size;
            if (PyDict_SetItem(result, key, value) < 0) {
                Py_DECREF(key);
                Py_DECREF(value);
                goto error;
            }
            Py_DECREF(key);
            Py_DECREF(value);
        } else if (key_is_int && val_is_int && !key_signed && !val_signed && key_byte_size <= 8 && val_byte_size <= 8) {
            const unsigned char *buf2 = base + current_offset;
            Py_ssize_t remaining2 = buf_len - current_offset;
            unsigned long long key_num = 0;
            Py_ssize_t key_size = 0;
            if (key_byte_size > 0) {
                if (remaining2 < key_byte_size) {
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to decode key");
                    goto error;
                }
                key_num = nativeseq_load_value(buf2, key_byte_size);
                key_size = key_byte_size;
            } else {
                if (decode_varint_ull(buf2, remaining2, &key_num, &key_size) < 0) {
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to decode key");
                    goto error;
                }
            }
            PyObject *key_num_obj = PyLong_FromUnsignedLongLong(key_num);
            if (!key_num_obj) {
                goto error;
            }
            PyObject *key = PyObject_CallFunctionObjArgs(key_type, key_num_obj, NULL);
            Py_DECREF(key_num_obj);
            if (!key) {
                goto error;
            }
            current_offset += key_size;
            buf2 = base + current_offset;
            remaining2 = buf_len - current_offset;
            unsigned long long value_num = 0;
            Py_ssize_t value_size = 0;
            if (val_byte_size > 0) {
                if (remaining2 < val_byte_size) {
                    Py_DECREF(key);
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to decode value");
                    goto error;
                }
                value_num = nativeseq_load_value(buf2, val_byte_size);
                value_size = val_byte_size;
            } else {
                if (decode_varint_ull(buf2, remaining2, &value_num, &value_size) < 0) {
                    Py_DECREF(key);
                    PyErr_SetString(PyExc_ValueError, "Buffer too small to decode value");
                    goto error;
                }
            }
            PyObject *val_num_obj = PyLong_FromUnsignedLongLong(value_num);
            if (!val_num_obj) {
                Py_DECREF(key);
                goto error;
            }
            PyObject *value = PyObject_CallFunctionObjArgs(value_type, val_num_obj, NULL);
            Py_DECREF(val_num_obj);
            if (!value) {
                Py_DECREF(key);
                goto error;
            }
            current_offset += value_size;
            if (PyDict_SetItem(result, key, value) < 0) {
                Py_DECREF(key);
                Py_DECREF(value);
                goto error;
            }
            Py_DECREF(key);
            Py_DECREF(value);
        } else {
            PyObject *key = NULL;
            Py_ssize_t key_size = 0;
            if (call_decode_from(key_type, buf_obj, current_offset, &key, &key_size) < 0) {
                goto error;
            }
            current_offset += key_size;
            PyObject *value = NULL;
            Py_ssize_t val_size = 0;
            if (call_decode_from(value_type, buf_obj, current_offset, &value, &val_size) < 0) {
                Py_DECREF(key);
                goto error;
            }
            current_offset += val_size;
            if (PyDict_SetItem(result, key, value) < 0) {
                Py_DECREF(key);
                Py_DECREF(value);
                goto error;
            }
            Py_DECREF(key);
            Py_DECREF(value);
        }
    }
    ret = Py_BuildValue("Nn", result, current_offset - offset);
    result = NULL;

error:
    Py_XDECREF(result);
    Py_XDECREF(key_type);
    Py_XDECREF(value_type);
    PyBuffer_Release(&view);
    return ret;
}

static PyObject *
NativeDict_decode(PyObject *cls, PyObject *args) {
    PyObject *tuple = NativeDict_decode_from(cls, args);
    if (!tuple) {
        return NULL;
    }
    if (!PyTuple_Check(tuple) || PyTuple_GET_SIZE(tuple) < 1) {
        Py_DECREF(tuple);
        PyErr_SetString(PyExc_ValueError, "Invalid decode_from result");
        return NULL;
    }
    PyObject *value = PyTuple_GET_ITEM(tuple, 0);
    Py_INCREF(value);
    Py_DECREF(tuple);
    return value;
}

static PyObject *
NativeDict_to_json(PyObject *self, PyObject *Py_UNUSED(ignored)) {
    PyObject *out = PyDict_New();
    if (!out) {
        return NULL;
    }
    PyObject *keys = PyDict_Keys(self);
    if (!keys) {
        Py_DECREF(out);
        return NULL;
    }
    Py_ssize_t count = PyList_GET_SIZE(keys);
    for (Py_ssize_t i = 0; i < count; i++) {
        PyObject *key = PyList_GET_ITEM(keys, i);
        PyObject *value = PyDict_GetItem(self, key);
        if (!value) {
            Py_DECREF(keys);
            Py_DECREF(out);
            PyErr_SetString(PyExc_KeyError, "Key not found during JSON encode");
            return NULL;
        }
        PyObject *key_json = PyObject_CallMethod(key, "to_json", NULL);
        if (!key_json) {
            Py_DECREF(keys);
            Py_DECREF(out);
            return NULL;
        }
        PyObject *val_json = PyObject_CallMethod(value, "to_json", NULL);
        if (!val_json) {
            Py_DECREF(key_json);
            Py_DECREF(keys);
            Py_DECREF(out);
            return NULL;
        }
        if (PyDict_SetItem(out, key_json, val_json) < 0) {
            Py_DECREF(key_json);
            Py_DECREF(val_json);
            Py_DECREF(keys);
            Py_DECREF(out);
            return NULL;
        }
        Py_DECREF(key_json);
        Py_DECREF(val_json);
    }
    Py_DECREF(keys);
    return out;
}

static PyObject *
NativeDict_from_json(PyObject *cls, PyObject *args) {
    PyObject *data;
    if (!PyArg_ParseTuple(args, "O", &data)) {
        return NULL;
    }
    PyObject *key_type = NULL;
    PyObject *value_type = NULL;
    if (dict_get_types(cls, &key_type, &value_type) < 0) {
        return NULL;
    }
    PyObject *result = PyObject_CallObject(cls, NULL);
    if (!result) {
        Py_DECREF(key_type);
        Py_DECREF(value_type);
        return NULL;
    }
    if (PyDict_Check(data)) {
        PyObject *items = PyDict_Items(data);
        if (!items) {
            Py_DECREF(key_type);
            Py_DECREF(value_type);
            Py_DECREF(result);
            return NULL;
        }
        Py_ssize_t count = PyList_GET_SIZE(items);
        for (Py_ssize_t i = 0; i < count; i++) {
            PyObject *item = PyList_GET_ITEM(items, i);
            if (!PyTuple_Check(item) || PyTuple_GET_SIZE(item) < 2) {
                Py_DECREF(items);
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(result);
                PyErr_SetString(PyExc_ValueError, "Invalid JSON dict item");
                return NULL;
            }
            PyObject *k = PyTuple_GET_ITEM(item, 0);
            PyObject *v = PyTuple_GET_ITEM(item, 1);
            PyObject *key = PyObject_CallMethod(key_type, "from_json", "O", k);
            if (!key) {
                Py_DECREF(items);
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(result);
                return NULL;
            }
            PyObject *val = PyObject_CallMethod(value_type, "from_json", "O", v);
            if (!val) {
                Py_DECREF(key);
                Py_DECREF(items);
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(result);
                return NULL;
            }
            if (PyDict_SetItem(result, key, val) < 0) {
                Py_DECREF(key);
                Py_DECREF(val);
                Py_DECREF(items);
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(result);
                return NULL;
            }
            Py_DECREF(key);
            Py_DECREF(val);
        }
        Py_DECREF(items);
    } else {
        PyObject *key_name = PyObject_GetAttrString(cls, "_key_name");
        PyObject *value_name = PyObject_GetAttrString(cls, "_value_name");
        if (!key_name || !value_name) {
            Py_XDECREF(key_name);
            Py_XDECREF(value_name);
            Py_DECREF(key_type);
            Py_DECREF(value_type);
            Py_DECREF(result);
            PyErr_SetString(PyExc_ValueError, "Missing key/value names for JSON list input");
            return NULL;
        }
        if (key_name == Py_None || value_name == Py_None) {
            Py_DECREF(key_name);
            Py_DECREF(value_name);
            Py_DECREF(key_type);
            Py_DECREF(value_type);
            Py_DECREF(result);
            PyErr_SetString(PyExc_ValueError, "Missing key/value names for JSON list input");
            return NULL;
        }
        PyObject *seq = PySequence_Fast(data, "data must be a sequence");
        if (!seq) {
            Py_DECREF(key_name);
            Py_DECREF(value_name);
            Py_DECREF(key_type);
            Py_DECREF(value_type);
            Py_DECREF(result);
            return NULL;
        }
        Py_ssize_t count = PySequence_Fast_GET_SIZE(seq);
        PyObject **items = PySequence_Fast_ITEMS(seq);
        for (Py_ssize_t i = 0; i < count; i++) {
            PyObject *item = items[i];
            PyObject *k = PyObject_GetItem(item, key_name);
            PyObject *v = PyObject_GetItem(item, value_name);
            if (!k || !v) {
                Py_XDECREF(k);
                Py_XDECREF(v);
                Py_DECREF(seq);
                Py_DECREF(key_name);
                Py_DECREF(value_name);
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(result);
                return NULL;
            }
            PyObject *key = PyObject_CallMethod(key_type, "from_json", "O", k);
            Py_DECREF(k);
            if (!key) {
                Py_DECREF(v);
                Py_DECREF(seq);
                Py_DECREF(key_name);
                Py_DECREF(value_name);
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(result);
                return NULL;
            }
            PyObject *val = PyObject_CallMethod(value_type, "from_json", "O", v);
            Py_DECREF(v);
            if (!val) {
                Py_DECREF(key);
                Py_DECREF(seq);
                Py_DECREF(key_name);
                Py_DECREF(value_name);
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(result);
                return NULL;
            }
            if (PyDict_SetItem(result, key, val) < 0) {
                Py_DECREF(key);
                Py_DECREF(val);
                Py_DECREF(seq);
                Py_DECREF(key_name);
                Py_DECREF(value_name);
                Py_DECREF(key_type);
                Py_DECREF(value_type);
                Py_DECREF(result);
                return NULL;
            }
            Py_DECREF(key);
            Py_DECREF(val);
        }
        Py_DECREF(seq);
        Py_DECREF(key_name);
        Py_DECREF(value_name);
    }
    Py_DECREF(key_type);
    Py_DECREF(value_type);
    return result;
}

static PyMethodDef NativeDict_methods[] = {
    {"encode_size", NativeDict_encode_size, METH_NOARGS, "Encoded size."},
    {"encode_into", (PyCFunction)NativeDict_encode_into, METH_VARARGS | METH_KEYWORDS, "Encode into buffer."},
    {"decode_from", NativeDict_decode_from, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {"decode", NativeDict_decode, METH_CLASS | METH_VARARGS, "Decode from buffer."},
    {"to_json", NativeDict_to_json, METH_NOARGS, "Convert to JSON."},
    {"from_json", NativeDict_from_json, METH_CLASS | METH_VARARGS, "Create from JSON."},
    {NULL, NULL, 0, NULL},
};

static PyTypeObject NativeDictType = {
    PyVarObject_HEAD_INIT(NULL, 0)
    .tp_name = "tsrkit_types._native.NativeDict",
    .tp_basicsize = sizeof(PyDictObject),
    .tp_flags = Py_TPFLAGS_DEFAULT | Py_TPFLAGS_BASETYPE,
    .tp_methods = NativeDict_methods,
    .tp_base = &PyDict_Type,
};

static PyMethodDef NativeMethods[] = {
    {"uint_encode", uint_encode, METH_VARARGS, "Encode an integer to bytes."},
    {"uint_decode", uint_decode, METH_VARARGS, "Decode an integer from bytes."},
    {"pack_bits", pack_bits, METH_VARARGS, "Pack bits into bytes."},
    {"unpack_bits", unpack_bits, METH_VARARGS, "Unpack bytes into bits."},
    {"bits_validate", bits_validate, METH_VARARGS, "Validate a bits sequence."},
    {"bits_validate_one", bits_validate_one, METH_VARARGS, "Validate a single bit value."},
    {"seq_validate", seq_validate, METH_VARARGS, "Validate a typed sequence."},
    {"seq_validate_one", seq_validate_one, METH_VARARGS, "Validate a single typed element."},
    {"encode_fixed_array", encode_fixed_array, METH_VARARGS, "Encode fixed-width integer array."},
    {"decode_fixed_array", decode_fixed_array, METH_VARARGS, "Decode fixed-width integer array."},
    {NULL, NULL, 0, NULL},
};

static struct PyModuleDef native_module = {
    PyModuleDef_HEAD_INIT,
    "_native",
    "Native accelerators for tsrkit_types.",
    -1,
    NativeMethods,
};

PyMODINIT_FUNC
PyInit__native(void) {
    PyObject *module = PyModule_Create(&native_module);
    if (!module) {
        return NULL;
    }
    if (PyType_Ready(&NativeBitsType) < 0) {
        Py_DECREF(module);
        return NULL;
    }
    if (PyType_Ready(&NativeTypedSeqType) < 0) {
        Py_DECREF(module);
        return NULL;
    }
    if (PyType_Ready(&NativeBytesType) < 0) {
        Py_DECREF(module);
        return NULL;
    }
    if (PyType_Ready(&NativeByteArrayType) < 0) {
        Py_DECREF(module);
        return NULL;
    }
    if (PyType_Ready(&NativeDictType) < 0) {
        Py_DECREF(module);
        return NULL;
    }
    Py_INCREF(&NativeBitsType);
    if (PyModule_AddObject(module, "NativeBits", (PyObject *)&NativeBitsType) < 0) {
        Py_DECREF(&NativeBitsType);
        Py_DECREF(module);
        return NULL;
    }
    Py_INCREF(&NativeTypedSeqType);
    if (PyModule_AddObject(module, "NativeTypedSeq", (PyObject *)&NativeTypedSeqType) < 0) {
        Py_DECREF(&NativeTypedSeqType);
        Py_DECREF(module);
        return NULL;
    }
    Py_INCREF(&NativeBytesType);
    if (PyModule_AddObject(module, "NativeBytes", (PyObject *)&NativeBytesType) < 0) {
        Py_DECREF(&NativeBytesType);
        Py_DECREF(module);
        return NULL;
    }
    Py_INCREF(&NativeByteArrayType);
    if (PyModule_AddObject(module, "NativeByteArray", (PyObject *)&NativeByteArrayType) < 0) {
        Py_DECREF(&NativeByteArrayType);
        Py_DECREF(module);
        return NULL;
    }
    Py_INCREF(&NativeDictType);
    if (PyModule_AddObject(module, "NativeDict", (PyObject *)&NativeDictType) < 0) {
        Py_DECREF(&NativeDictType);
        Py_DECREF(module);
        return NULL;
    }
    return module;
}
