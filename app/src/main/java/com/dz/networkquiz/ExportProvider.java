package com.dz.networkquiz;

import android.content.ContentProvider;
import android.content.ContentValues;
import android.database.Cursor;
import android.database.MatrixCursor;
import android.net.Uri;
import android.os.ParcelFileDescriptor;
import android.provider.OpenableColumns;

import java.io.File;
import java.io.FileNotFoundException;

public class ExportProvider extends ContentProvider {
    static final String AUTHORITY = "com.dz.networkquiz.export";
    static final String EXPORT_NAME = "wrong_questions.md";

    @Override
    public boolean onCreate() {
        return true;
    }

    @Override
    public String getType(Uri uri) {
        return "text/markdown";
    }

    @Override
    public Cursor query(Uri uri, String[] projection, String selection, String[] selectionArgs, String sortOrder) {
        File file = exportFile(uri);
        MatrixCursor cursor = new MatrixCursor(new String[]{OpenableColumns.DISPLAY_NAME, OpenableColumns.SIZE});
        cursor.addRow(new Object[]{file.getName(), file.exists() ? file.length() : 0});
        return cursor;
    }

    @Override
    public ParcelFileDescriptor openFile(Uri uri, String mode) throws FileNotFoundException {
        return ParcelFileDescriptor.open(exportFile(uri), ParcelFileDescriptor.MODE_READ_ONLY);
    }

    @Override
    public Uri insert(Uri uri, ContentValues values) {
        return null;
    }

    @Override
    public int delete(Uri uri, String selection, String[] selectionArgs) {
        return 0;
    }

    @Override
    public int update(Uri uri, ContentValues values, String selection, String[] selectionArgs) {
        return 0;
    }

    private File exportFile(Uri uri) {
        File dir = new File(getContext().getCacheDir(), "exports");
        String name = uri == null ? EXPORT_NAME : uri.getLastPathSegment();
        if (name == null || name.length() == 0) {
            name = EXPORT_NAME;
        }
        name = name.replace("/", "_").replace("\\", "_");
        return new File(dir, name);
    }
}
