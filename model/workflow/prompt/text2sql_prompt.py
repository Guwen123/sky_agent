"""
Text2SQL 相关的Prompt模板
"""

# sky_take_out 数据库查询Prompt
SKY_TAKE_OUT_SQL_PROMPT = """
你是一个SQL专家，请根据用户的自然语言查询生成MySQL SQL语句。

数据库表结构：
1. dish表：
   - id: 主键
   - name: 菜品名称
   - category_id: 分类ID
   - price: 价格
   - image: 图片
   - description: 描述
   - status: 状态
   - create_time: 创建时间
   - update_time: 更新时间

2. dish_flavor表：
   - id: 主键
   - dish_id: 菜品ID（外键，关联dish表的id）
   - name: 口味名称
   - value: 口味值（如：不辣、微辣、中辣、特辣等）

示例：
用户查询：查询所有菜品
SQL语句：SELECT * FROM dish;

用户查询：查询名称包含'鱼'的菜品
SQL语句：SELECT * FROM dish WHERE name LIKE '%鱼%';

用户查询：查询价格在20到50元之间的菜品
SQL语句：SELECT * FROM dish WHERE price BETWEEN 20 AND 50;

用户查询：查询微辣口味的菜品
SQL语句：SELECT d.* FROM dish d JOIN dish_flavor df ON d.id = df.dish_id WHERE df.value = '微辣';

用户查询：{user_query}

请生成合适的SQL语句，只返回SQL语句本身，不要有任何解释。
"""

# hmdp 数据库 - 查询指定店铺评价的Prompt
HMDP_SHOP_COMMENTS_BY_ID_PROMPT = """
你是一个SQL专家，请生成MySQL SQL语句来查询指定店铺的评价信息。

数据库表结构：
1. tb_blog表（探店博客表）：
   - id: 主键
   - shop_id: 商户ID
   - user_id: 用户ID
   - title: 标题
   - images: 探店照片
   - content: 探店文字描述
   - liked: 点赞数量
   - comments: 评论数量
   - create_time: 创建时间
   - update_time: 更新时间

2. tb_user表（用户表）：
   - id: 主键
   - phone: 手机号码
   - password: 密码
   - nick_name: 昵称
   - icon: 头像
   - create_time: 创建时间
   - update_time: 更新时间

示例：
用户查询：查询店铺ID为1的所有评价信息
SQL语句：SELECT b.*, u.nick_name as user_name FROM tb_blog b LEFT JOIN tb_user u ON b.user_id = u.id WHERE b.shop_id = 1 ORDER BY b.create_time DESC;

查询要求：查询店铺ID为{shop_id}的所有评价信息，包括用户昵称，按创建时间倒序排列。

请生成合适的SQL语句，只返回SQL语句本身，不要有任何解释。
"""

# hmdp 数据库 - 查询所有店铺评价的Prompt
HMDP_ALL_SHOP_COMMENTS_PROMPT = """
你是一个SQL专家，请生成MySQL SQL语句来查询所有店铺的评价信息。

数据库表结构：
1. tb_blog表（探店博客表）：
   - id: 主键
   - shop_id: 商户ID
   - user_id: 用户ID
   - title: 标题
   - images: 探店照片
   - content: 探店文字描述
   - liked: 点赞数量
   - comments: 评论数量
   - create_time: 创建时间
   - update_time: 更新时间

2. tb_user表（用户表）：
   - id: 主键
   - phone: 手机号码
   - password: 密码
   - nick_name: 昵称
   - icon: 头像
   - create_time: 创建时间
   - update_time: 更新时间

3. tb_shop表（商铺表）：
   - id: 主键
   - name: 商铺名称
   - type_id: 商铺类型ID
   - images: 商铺图片
   - area: 商圈
   - address: 地址
   - x: 经度
   - y: 维度
   - avg_price: 均价
   - sold: 销量
   - comments: 评论数量
   - score: 评分
   - open_hours: 营业时间
   - create_time: 创建时间
   - update_time: 更新时间

示例：
用户查询：查询所有店铺的评价信息
SQL语句：SELECT b.*, u.nick_name as user_name, s.name as shop_name FROM tb_blog b LEFT JOIN tb_user u ON b.user_id = u.id LEFT JOIN tb_shop s ON b.shop_id = s.id ORDER BY b.create_time DESC;

查询要求：查询所有店铺的评价信息，包括用户昵称和店铺名称，按创建时间倒序排列。

请生成合适的SQL语句，只返回SQL语句本身，不要有任何解释。
"""
