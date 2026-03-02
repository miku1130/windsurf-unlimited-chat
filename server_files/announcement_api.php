<?php
/**
 * 公告管理 API
 * 用于保存和读取公告内容
 * 支持 CORS 跨域访问
 */

// CORS 头
header('Access-Control-Allow-Origin: *');
header('Access-Control-Allow-Methods: GET, POST, OPTIONS');
header('Access-Control-Allow-Headers: Content-Type');
header('Content-Type: application/json; charset=utf-8');

// OPTIONS 预检请求
if ($_SERVER['REQUEST_METHOD'] === 'OPTIONS') {
    http_response_code(204);
    exit;
}

$json_file = __DIR__ . '/announcement.json';

// GET - 获取公告
if ($_SERVER['REQUEST_METHOD'] === 'GET') {
    if (file_exists($json_file)) {
        $data = file_get_contents($json_file);
        echo $data;
    } else {
        echo json_encode(['content' => '', 'enabled' => false, 'updated_at' => '']);
    }
    exit;
}

// POST - 保存公告（需要密码验证）
if ($_SERVER['REQUEST_METHOD'] === 'POST') {
    $input = json_decode(file_get_contents('php://input'), true);
    
    // 简单密码验证
    $password = $input['password'] ?? '';
    if ($password !== 'lemon2024') {
        http_response_code(403);
        echo json_encode(['success' => false, 'message' => '密码错误']);
        exit;
    }
    
    $data = [
        'content' => $input['content'] ?? '',
        'enabled' => (bool)($input['enabled'] ?? false),
        'updated_at' => date('Y-m-d H:i:s'),
    ];
    
    $result = file_put_contents($json_file, json_encode($data, JSON_UNESCAPED_UNICODE | JSON_PRETTY_PRINT));
    
    if ($result !== false) {
        echo json_encode(['success' => true, 'data' => $data]);
    } else {
        http_response_code(500);
        echo json_encode(['success' => false, 'message' => '写入文件失败']);
    }
    exit;
}

http_response_code(405);
echo json_encode(['error' => 'Method Not Allowed']);
