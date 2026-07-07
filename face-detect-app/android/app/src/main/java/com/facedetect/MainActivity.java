package com.facedetect;

import android.annotation.SuppressLint;
import android.app.Activity;
import android.content.ActivityNotFoundException;
import android.content.Context;
import android.content.Intent;
import android.content.SharedPreferences;
import android.content.pm.PackageManager;
import android.net.Uri;
import android.os.Build;
import android.os.Bundle;
import android.os.Environment;
import android.provider.MediaStore;
import android.view.KeyEvent;
import android.view.View;
import android.view.inputmethod.EditorInfo;
import android.webkit.ValueCallback;
import android.webkit.WebChromeClient;
import android.webkit.WebResourceRequest;
import android.webkit.WebSettings;
import android.webkit.WebView;
import android.webkit.WebViewClient;
import android.widget.ProgressBar;
import android.view.Menu;
import android.view.MenuItem;
import android.widget.Toast;

import androidx.annotation.NonNull;
import androidx.appcompat.app.AppCompatActivity;
import androidx.appcompat.widget.Toolbar;
import androidx.core.app.ActivityCompat;
import androidx.core.content.ContextCompat;
import androidx.core.content.FileProvider;

import java.io.File;
import java.io.IOException;
import java.text.SimpleDateFormat;
import java.util.Date;
import java.util.ArrayList;

public class MainActivity extends AppCompatActivity {

    private WebView webView;
    private ProgressBar progressBar;
    private static final int REQUEST_FILE_PICKER = 1001;
    private static final int REQUEST_PERMISSIONS = 1002;
    private ValueCallback<Uri[]> filePathCallback;
    private Uri cameraPhotoUri;
    private boolean needCameraCapture = false;

    // Default server address (change to your actual server IP/domain before building)
    private static final String DEFAULT_SERVER_URL = "http://YOUR_SERVER_IP:8000";

    private String currentServerUrl;

    @SuppressLint("SetJavaScriptEnabled")
    @Override
    protected void onCreate(Bundle savedInstanceState) {
        super.onCreate(savedInstanceState);
        setContentView(R.layout.activity_main);

        Toolbar toolbar = findViewById(R.id.toolbar);
        setSupportActionBar(toolbar);

        webView = findViewById(R.id.webview);
        progressBar = findViewById(R.id.progress_bar);

        WebSettings settings = webView.getSettings();
        settings.setJavaScriptEnabled(true);
        settings.setDomStorageEnabled(true);
        settings.setDatabaseEnabled(true);
        settings.setAllowFileAccess(true);
        settings.setAllowContentAccess(true);
        settings.setCacheMode(WebSettings.LOAD_NO_CACHE);
        settings.setMixedContentMode(WebSettings.MIXED_CONTENT_COMPATIBILITY_MODE);

        // Enable zoom for better UX
        settings.setSupportZoom(true);
        settings.setBuiltInZoomControls(true);
        settings.setDisplayZoomControls(false);

        webView.setWebViewClient(new WebViewClient() {
            @Override
            public boolean shouldOverrideUrlLoading(WebView view, WebResourceRequest request) {
                // Allow navigation within the app
                return false;
            }

            @Override
            public void onPageFinished(WebView view, String url) {
                progressBar.setVisibility(View.GONE);
            }
        });

        webView.setWebChromeClient(new WebChromeClient() {
            @Override
            public boolean onShowFileChooser(
                    WebView webView,
                    ValueCallback<Uri[]> filePathCallback,
                    FileChooserParams fileChooserParams) {
                MainActivity.this.filePathCallback = filePathCallback;

                // Check if camera capture is requested (e.g. capture="camera" attribute)
                boolean acceptCamera = false;
                if (fileChooserParams.getMode() == FileChooserParams.MODE_OPEN) {
                    // Check if camera option is available
                    acceptCamera = fileChooserParams.isCaptureEnabled();
                }

                if (checkPermissions(acceptCamera)) {
                    launchFileChooser(fileChooserParams);
                } else {
                    needCameraCapture = acceptCamera;
                    requestPermissions();
                }
                return true;
            }

            @Override
            public void onProgressChanged(WebView view, int newProgress) {
                if (newProgress < 100 && progressBar.getVisibility() == View.GONE) {
                    progressBar.setVisibility(View.VISIBLE);
                }
                progressBar.setProgress(newProgress);
                if (newProgress == 100) {
                    progressBar.setVisibility(View.GONE);
                }
            }
        });

        // Inject server config into the page
        webView.addJavascriptInterface(new JsBridge(this), "AndroidBridge");

        // Load the frontend
        currentServerUrl = getServerUrl();
        if (currentServerUrl.endsWith("/")) currentServerUrl = currentServerUrl.substring(0, currentServerUrl.length() - 1);
        webView.loadUrl(currentServerUrl + "/");
        progressBar.setVisibility(View.VISIBLE);

        // Request permissions on app startup
        if (!checkAllPermissions()) {
            requestPermissions();
        }
    }

    @Override
    protected void onResume() {
        super.onResume();
        String newUrl = getServerUrl();
        String normalizedNew = newUrl.endsWith("/") ? newUrl.substring(0, newUrl.length() - 1) : newUrl;
        if (!normalizedNew.equals(currentServerUrl)) {
            currentServerUrl = normalizedNew;
            webView.loadUrl(currentServerUrl + "/");
            progressBar.setVisibility(View.VISIBLE);
        }
    }

    private String getServerUrl() {
        SharedPreferences prefs = getSharedPreferences(SettingsActivity.PREFS_NAME, Context.MODE_PRIVATE);
        String saved = prefs.getString(SettingsActivity.KEY_SERVER_URL, DEFAULT_SERVER_URL);
        if (saved == null || saved.isEmpty()) return DEFAULT_SERVER_URL;
        return saved;
    }

    private boolean checkAllPermissions() {
        return hasStoragePermission() && hasCameraPermission();
    }

    private boolean hasStoragePermission() {
        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            return ContextCompat.checkSelfPermission(this,
                    android.Manifest.permission.READ_MEDIA_IMAGES) == PackageManager.PERMISSION_GRANTED;
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            return ContextCompat.checkSelfPermission(this,
                    android.Manifest.permission.READ_EXTERNAL_STORAGE) == PackageManager.PERMISSION_GRANTED;
        }
        return true;
    }

    private boolean hasCameraPermission() {
        return ContextCompat.checkSelfPermission(this,
                android.Manifest.permission.CAMERA) == PackageManager.PERMISSION_GRANTED;
    }

    // Check specific permissions (for file chooser callback)
    private boolean checkPermissions(boolean needCamera) {
        boolean hasStorage = hasStoragePermission();
        boolean hasCamera = !needCamera || hasCameraPermission();
        return hasStorage && hasCamera;
    }

    private void requestPermissions() {
        ArrayList<String> permissions = new ArrayList<>();

        if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.TIRAMISU) {
            if (ContextCompat.checkSelfPermission(this,
                    android.Manifest.permission.READ_MEDIA_IMAGES)
                    != PackageManager.PERMISSION_GRANTED) {
                permissions.add(android.Manifest.permission.READ_MEDIA_IMAGES);
            }
        } else if (Build.VERSION.SDK_INT >= Build.VERSION_CODES.M) {
            if (ContextCompat.checkSelfPermission(this,
                    android.Manifest.permission.READ_EXTERNAL_STORAGE)
                    != PackageManager.PERMISSION_GRANTED) {
                permissions.add(android.Manifest.permission.READ_EXTERNAL_STORAGE);
            }
        }

        if (ContextCompat.checkSelfPermission(this,
                android.Manifest.permission.CAMERA)
                != PackageManager.PERMISSION_GRANTED) {
            permissions.add(android.Manifest.permission.CAMERA);
        }

        if (!permissions.isEmpty()) {
            String[] permArray = permissions.toArray(new String[0]);
            ActivityCompat.requestPermissions(this, permArray, REQUEST_PERMISSIONS);
        }
    }

    private void launchFileChooser(WebChromeClient.FileChooserParams params) {
        // Check if camera capture is specifically requested
        boolean captureEnabled = params.isCaptureEnabled();

        Intent takePictureIntent = null;
        if (captureEnabled && hasCameraPermission()) {
            try {
                cameraPhotoUri = createImageFile();
                takePictureIntent = new Intent(MediaStore.ACTION_IMAGE_CAPTURE);
                if (takePictureIntent.resolveActivity(getPackageManager()) != null) {
                    takePictureIntent.putExtra(MediaStore.EXTRA_OUTPUT, cameraPhotoUri);
                    takePictureIntent.addFlags(Intent.FLAG_GRANT_WRITE_URI_PERMISSION
                            | Intent.FLAG_GRANT_READ_URI_PERMISSION);
                } else {
                    cameraPhotoUri = null;
                    takePictureIntent = null;
                }
            } catch (IOException e) {
                cameraPhotoUri = null;
                takePictureIntent = null;
                Toast.makeText(this, "无法创建拍照文件", Toast.LENGTH_SHORT).show();
            }
        }

        Intent contentIntent = params.createIntent();

        if (takePictureIntent != null) {
            // Combine camera + file picker
            ArrayList<Intent> intents = new ArrayList<>();
            intents.add(takePictureIntent);
            intents.add(contentIntent);

            Intent chooser = Intent.createChooser(contentIntent, "选择来源");
            chooser.putExtra(Intent.EXTRA_INITIAL_INTENTS,
                    new android.os.Parcelable[]{takePictureIntent});
            try {
                startActivityForResult(chooser, REQUEST_FILE_PICKER);
            } catch (ActivityNotFoundException e) {
                filePathCallback.onReceiveValue(null);
                filePathCallback = null;
                Toast.makeText(this, "无法打开相机或文件选择器", Toast.LENGTH_SHORT).show();
            }
        } else {
            // Just file picker
            try {
                startActivityForResult(contentIntent, REQUEST_FILE_PICKER);
            } catch (ActivityNotFoundException e) {
                filePathCallback.onReceiveValue(null);
                filePathCallback = null;
                Toast.makeText(this, "无法打开文件选择器", Toast.LENGTH_SHORT).show();
            }
        }
    }

    private Uri createImageFile() throws IOException {
        String timeStamp = new SimpleDateFormat("yyyyMMdd_HHmmss").format(new Date());
        String imageFileName = "FD_" + timeStamp + "_";
        File storageDir = getExternalFilesDir(Environment.DIRECTORY_PICTURES);
        if (storageDir == null) {
            throw new IOException("无法访问存储目录");
        }
        File image = File.createTempFile(imageFileName, ".jpg", storageDir);
        return FileProvider.getUriForFile(this,
                getApplicationContext().getPackageName() + ".provider", image);
    }

    @Override
    public void onRequestPermissionsResult(int requestCode,
                                           @NonNull String[] permissions,
                                           @NonNull int[] grantResults) {
        super.onRequestPermissionsResult(requestCode, permissions, grantResults);
        if (requestCode == REQUEST_PERMISSIONS) {
            boolean allGranted = true;
            for (int i = 0; i < grantResults.length; i++) {
                if (grantResults[i] != PackageManager.PERMISSION_GRANTED) {
                    allGranted = false;
                    String perm = permissions[i];
                    if (android.Manifest.permission.CAMERA.equals(perm)) {
                        Toast.makeText(this, "需要相机权限才能拍照", Toast.LENGTH_LONG).show();
                    } else {
                        Toast.makeText(this, "需要存储权限才能上传图片", Toast.LENGTH_LONG).show();
                    }
                }
            }
            if (allGranted) {
                Toast.makeText(this, "权限已获取", Toast.LENGTH_SHORT).show();
            }
        }
    }

    @Override
    protected void onActivityResult(int requestCode, int resultCode, Intent data) {
        super.onActivityResult(requestCode, resultCode, data);

        if (requestCode == REQUEST_FILE_PICKER) {
            Uri[] results = null;

            if (resultCode == Activity.RESULT_OK) {
                if (data == null) {
                    // Could be camera capture (data is null when using EXTRA_OUTPUT)
                    if (cameraPhotoUri != null) {
                        results = new Uri[]{cameraPhotoUri};
                    }
                } else {
                    if (data.getData() != null) {
                        results = new Uri[]{data.getData()};
                    } else if (data.getClipData() != null) {
                        int count = data.getClipData().getItemCount();
                        results = new Uri[count];
                        for (int i = 0; i < count; i++) {
                            results[i] = data.getClipData().getItemAt(i).getUri();
                        }
                    }
                }
            }

            // Reset camera uri for next use
            cameraPhotoUri = null;

            if (filePathCallback != null) {
                filePathCallback.onReceiveValue(results);
                filePathCallback = null;
            }
        }
    }

    @Override
    public boolean onKeyDown(int keyCode, KeyEvent event) {
        if (keyCode == KeyEvent.KEYCODE_BACK && webView.canGoBack()) {
            webView.goBack();
            return true;
        }
        return super.onKeyDown(keyCode, event);
    }

    @Override
    protected void onDestroy() {
        webView.destroy();
        super.onDestroy();
    }

    @Override
    public boolean onCreateOptionsMenu(Menu menu) {
        getMenuInflater().inflate(R.menu.toolbar_menu, menu);
        return true;
    }

    @Override
    public boolean onOptionsItemSelected(@NonNull MenuItem item) {
        if (item.getItemId() == R.id.action_settings) {
            Intent intent = new Intent(MainActivity.this, SettingsActivity.class);
            startActivity(intent);
            return true;
        }
        return super.onOptionsItemSelected(item);
    }
}
